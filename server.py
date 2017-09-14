import zmq
import time
import timeit as ti
from helper import Proto, switch
import scgame
import sdl2
import collision
import ui
import drawable as draw
import scgameobjects as scgo

# Globals
g_zmqhwm = 1024

class Server(scgame.scgame):
    # To track clients, use dictionary of connections where:
    # key = client assigned identity
    # value = 4 element nested dict of:
    #    imc = incoming message count
    #    ibr = incoming bytes recv'd,
    #    omc = outgoing message count
    #    obs = outgoing bytes sent

    def __init__(self, server_port):
        context = zmq.Context().instance()
        self.socket = context.socket(zmq.ROUTER)
        self.socket.setsockopt(zmq.SNDHWM, g_zmqhwm)
        self.socket.setsockopt(zmq.RCVHWM, g_zmqhwm)
        self.socket.bind("tcp://*:%s" % server_port)
        # set up a read poller
        self.poller = zmq.Poller()
        self.poller.register(self.socket, zmq.POLLIN)
        self.clientmap = dict()
        # remove later
        self.vx = 0.0
        self.fire = False
        print "Server bound to port: " + str(server_port)

    def serverrun(self, runtime):
        print "Server: start run"

        # Server's idle loop
        # Note: artificially running for a fixed number of seconds
        timeout = 1 # int(1.0/60.0)
        running = True
        self.lastDelta = 0.0
        quitLimit = 2.0
        quitTimer = 0.0
        pingLimit = 5.0
        pingTimer = 0.0
        super(Server, self).__init__()
        self.setup()
        while running:
            start = ti.default_timer()

            if not self.gameIsActive:
                quitTimer += self.lastDelta
                if (quitTimer >= quitLimit):
                    break

            # Read incoming
            sockets = dict(self.poller.poll(timeout))
            if self.socket in sockets and sockets[self.socket] == zmq.POLLIN:
                id, data = self.socket.recv_multipart()
                self.parseMsg(id, data)

            running = self.run()

            # Send ping outgoing to all clients every X seconds
            pingTimer += self.lastDelta
            if (pingTimer >= pingLimit):
                for id in self.clientmap.iterkeys():
                    self.send(id, Proto.ping)
                pingTimer = 0.0

            stop = ti.default_timer()
            self.lastDelta = stop - start
            # Sleep if frame rate is higher than desired
            if (self.limitFrame and (self.lastDelta < self.minFrameSecs)):
                time.sleep(self.minFrameSecs - self.lastDelta)
                stop = ti.default_timer()
                self.lastDelta = stop - start

        self.shutdown()

        # Force disconnect/kill all clients
        print "Server: shutting down..."
        for id in self.clientmap.iterkeys():
            self.send(id, Proto.serverstop)

        print self.clientmap
        self.socket.close()
        print "Server: end run"

    def send(self, id, proto, data = b''):
        final = proto + data
        self.socket.send_multipart([id, final])
        # update send stats
        usage = self.clientmap[id]
        usage['omc'] += 1
        usage['obs'] += len(final)

    def parseMsg(self, id, msg):
        header = msg[0:Proto.headerlen]
        body = msg[Proto.headerlen:]
        # if header != Proto.str:
            # print "Proto: " + header + " data: " + body

        # Check if client is registered -- this is messy
        if not id in self.clientmap and not header == Proto.greet:
            print "Server: recv'd msg from unregistered client"
            # TODO: debug
            return

        for case in switch(header):
            if case(Proto.greet):
                colorsplit = body.split(":")
                color = sdl2.ext.Color(int(colorsplit[0]), int(colorsplit[1]), int(colorsplit[2]), 255)
                self.addClient(id, color)
                break
            if case(Proto.str):
                print "Server: client string: (" + id + ") " + body
                break
            if case(Proto.ping):
                print "Server: client ping: (" + id + ")"
                break
            if case(Proto.clientstop):
                self.removeClient(id, body)
                break
            if case(Proto.clientmove):
                self.clientmap[id]['vx'] = float(body)
                # print "Moving client. vx = " + str(self.vx)
                self.moveClients(id, float(body))
                break
            if case(Proto.clientfire):
                self.clientmap[id]['fire'] = True
                self.fireClients(id)
                break
            if case(Proto.lostlife):
                break
            if case():  # default
                print "Server: received undefined message!"
                # TODO: debug

        # update receive stats
        if (id in self.clientmap):
            usage = self.clientmap[id]
            usage['imc'] += 1
            usage['ibr'] += (Proto.headerlen + len(body))

    def addClient(self, id, body):
        if id in self.clientmap:
            print "Server: recv'd duplicate client reg"
            # TODO: debug
        else:
            print "Server: registering new client: " + id
            # save color in string format (body is sdl color format)
            colorstr = "%s:%s:%s" % (body.r, body.g, body.b)
            self.addPlayer(id, body)
            # add to clientmap
            self.clientmap[id] = {'imc': 0, 'ibr': 0, 'omc': 0, 'obs': 0, 'vx': 0,
                                  'fire': False, 'color': colorstr, 'lives': 3, 'score': 0}
            # reply with ack
            self.send(id, Proto.greet)

            # sync server game state to client
            # TODO destroyed enemies, etc

            # add new player to other clients, and other clients to new
            for otherid in self.clientmap.iterkeys():
                if (otherid != id):
                    othercolor = self.clientmap[otherid]['color']
                    body = "%s:%s" % (id, colorstr)
                    print "added new client: " + id + " to " + otherid + " body: " + body
                    # first add new to other
                    self.send(otherid, Proto.addclient, body)
                    # now add other to new
                    body = "%s:%s" % (otherid, othercolor)
                    self.send(id, Proto.addclient, body)

            print self.clientmap

    def removeClient(self, id, body):
        if id in self.clientmap:
            print "Server: removing client (" + id + ")"
            del self.clientmap[id]
        else:
            print "Attempt to remove unregistered client"
            # TODO: debug
        self.removePlayer(id)
        for otherid in self.clientmap.iterkeys():
            self.send(otherid, Proto.removeclient, id)

    def run(self):
        running = True
        # Update only if active
        if self.gameIsActive:
            running = self.update(self.lastDelta)

        # Setup framerate if enabled
        if self.options.debug and self.lastDelta > 0.0:
            self.fpsCounter.setText("FPS: " + str(int(1.0 / self.lastDelta)))

        # Always render
        self.render()

        return running

    def moveClients(self, id, vx):
        for otherid in self.clientmap.iterkeys():
            if otherid != id:
                body = "%s:%s" % (id, vx)
                self.send(otherid, Proto.moveother, body)

    def fireClients(self, id):
        for otherid in self.clientmap.iterkeys():
            if otherid != id:
                self.send(otherid, Proto.fireother, id)

    def livesChange(self, id, lives):
        self.clientmap[id]['lives'] = lives
        for otherid in self.clientmap.iterkeys():
            body = "%s:%s" % (id, lives)
            self.send(otherid, Proto.lostlife, body)

    def scoreChange(self, id, score, index):
        self.clientmap[id]['score'] = score
        for otherid in self.clientmap.iterkeys():
            body = "%s:%s:%s" % (id, score, index)
            self.send(otherid, Proto.scoreup, body)

    def enemyFire(self, enemy):
        body = str(enemy)
        for otherid in self.clientmap.iterkeys():
            self.send(otherid, Proto.enemyfire, body)

    def update(self, time):
        # our main game loop

        # read local inputs & events
        events = sdl2.ext.get_events()
        for event in events:
            if event.type == sdl2.SDL_QUIT:
                return False

        if self.gameIsActive:
            for player in self.players:
                # associate velocity with id in dictionary
                player.vx = self.clientmap[player.id]['vx']
                if self.clientmap[player.id]['fire']:
                    player.fire()
                    self.clientmap[player.id]['fire'] = False
                player.update(time)

            self.enemycontrol.serverupdate(time)

            if self.enemycontrol.serverfiring:
                self.enemyFire(self.enemycontrol.shooter)
                self.enemycontrol.serverfiring = False

            for player in self.players:
                if self.enemycontrol.checkWin(player):
                    # notify the client
                    self.send(player.id, Proto.clientwin)
                    self.gameover(player)

            for enemy in self.enemycontrol.enemies:
                enemy.update(time)

            for ebullet in self.enemycontrol.bullets:
                ebullet.update(time)
                #shield hit
                for shield in self.shields:
                    hit = collision.checkCollision(ebullet, shield)
                    if hit:
                        self.enemycontrol.removebullet(ebullet)
                        shield.hit()
                        if shield.health <= 0:
                            shield.remove()
                            self.shields.remove(shield)
                        break
                #player hit
                index = 0
                for player in self.players:
                    hit = collision.checkCollision(ebullet, player)
                    if hit:
                        # print "enemy hit"
                        self.enemycontrol.removebullet(ebullet)
                        player.lostlife()
                        self.livesChange(player.id, player.lives)
                        self.livesUI[player.id].updateLives(player.lives)
                        # print self.clientmap
                        if player.lives <= 0:
                            self.send(player.id, Proto.clientlose)
                        break
                    index += 1

            for player in self.players:
                index = 0
                for bullet in player.bullets:
                    bullet.update(time)
                    for shield in self.shields:
                        hit = collision.checkCollision(bullet, shield)
                        if hit:
                            player.removebullet(bullet)
                            shield.hit()
                            if shield.health <= 0:
                                shield.remove()
                                self.shields.remove(shield)
                            break
                    enemyindex = 0
                    for enemy in self.enemycontrol.enemies:
                        hit = collision.checkCollision(bullet, enemy)
                        if hit:
                            player.score += enemy.points
                            self.scoreChange(player.id, player.score, enemyindex)
                            self.scoreUI[player.id].updateScore(player.score)
                            enemy.remove()
                            self.enemycontrol.enemies.remove(enemy)
                            player.removebullet(bullet)
                            break
                        enemyindex += 1
                index += 1
            if len(self.enemycontrol.enemies) < 1:
                self.enemycontrol.reset()

        return True

    def setup(self):
        # create window
        self.width = self.options.width
        self.height = self.options.height

        self.window = sdl2.ext.Window("Space Invaders - Server", size=(self.width, self.height),
                                      position=(0,0))
    	self.window.show()

        # create renderer starting with a base sdl2ext renderer
        self.renderer = sdl2.ext.Renderer(self.window)
        # set all our renderer instance types
        draw.filledRect.setRenderer(self.renderer)
        draw.spriteMaker.setRenderer(self.renderer)
        draw.textMaker.setRenderer(self.renderer)

        ###########################################################################

        ###########################################################################
        # Our game object setup
        ###########################################################################

        self.enemycontrol = scgo.EnemyController(self.width, self.height)

        # creates shields
        x = .1
        while x <= .75:
            shield = scgo.Shield(x, .8, self.width, self.height)
            self.shields.append(shield)
            x += .30

        self.limitFrame = False
        frameRateLimit = 1.0
        if (self.options.limitFrameRate):
            self.limitFrame = True
            frameRateLimit = self.options.limitFrameRate
            print "--frame rate limit(%d)--" % frameRateLimit
        self.minFrameSecs = 1.0 / frameRateLimit

        if self.options.debug:
            self.fpsCounter = draw.textMaker("FPS: 0", self.width - 55, self.height - 14, 12,
                                      fontname="Arial.ttf")