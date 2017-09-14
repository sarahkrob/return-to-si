import time
import timeit as ti
import uuid
import zmq
from helper import Proto, switch
import scgame
import sdl2.ext
import sdl2
import drawable as draw
import scgameobjects as scgo
import collision

# Globals
g_zmqhwm = 1024

class Client(scgame.scgame):
    # client registration string

    def __init__(self, ipaddr, server_port):
        context = zmq.Context().instance()
        self.socket = context.socket(zmq.DEALER)
        # generate a universally unique client ID -- slicing last 12
        # characters of the UUID4 just to keep it shorter
        self.id = str(uuid.uuid4())[-12:]
        self.socket.setsockopt(zmq.IDENTITY, str(self.id))
        self.socket.setsockopt(zmq.SNDHWM, g_zmqhwm)
        self.socket.setsockopt(zmq.RCVHWM, g_zmqhwm)
        self.socket.connect("tcp://%s:%s" % (ipaddr, server_port))
        # set up a read poller
        self.poller = zmq.Poller()
        self.poller.register(self.socket, zmq.POLLIN)
        self.svr_connect = False
        # clientmap
        self.clientmap = dict()
        # setup game
        super(Client, self).__init__()
        self.setup(self.id)
        # get player color
        color = self.players[0].colormod
        colorstr = "%s:%s:%s" % (color.r, color.g, color.b)
        # add to clientmap
        self.players[0].id = self.id
        self.clientmap[self.id] = {'vx': 0, 'fire': False, 'lives': 3, 'score': 0}
        # send connection message that will register server with client
        print "Connecting to server..."
        self.send(Proto.greet, colorstr)
        # blocking read
        msg = self.socket.recv()
        self.parseMsg(msg)

        print "Client: " + str(self.id) + " connected to: " + ipaddr + ":" + str(server_port)

    def clientrun(self):
        print "Client: start run"

        # Client's idle loop
        timeout = 1
        self.lastDelta = 0.0
        quitLimit = 5.0
        quitTimer = 0.0
        pingLimit = 5.0
        pingTimer = 0.0

        while True:
            start = ti.default_timer()

            if not self.gameIsActive:
                quitTimer += self.lastDelta
                if (quitTimer >= quitLimit):
                    break

            # Read incoming
            sockets = dict(self.poller.poll(timeout))
            if self.socket in sockets and sockets[self.socket] == zmq.POLLIN:
                msg = self.socket.recv()
                if not self.parseMsg(msg):
                    # gameover state
                    self.gameover(self.players[0])
                    continue

            super(Client, self).run()

            if self.svr_connect:
                # will only have one local player, specify if player is local w/variable
                for player in self.players:
                    if player.id == self.id:
                        if player.move:
                            movevx = str(player.vx)
                            # print "Sending move message"
                            self.send(Proto.clientmove, movevx)
                            player.move = False
                        if player.shoot:
                            # print "Sending fire message"
                            self.send(Proto.clientfire)
                            player.shoot = False

            # Send ping to server every X seconds
            pingTimer += self.lastDelta
            if (pingTimer >= pingLimit):
                self.send(Proto.ping)
                pingTimer = 0.0

            stop = ti.default_timer()
            self.lastDelta = stop - start
            # Sleep if frame rate is higher than desired
            if (self.limitFrame and (self.lastDelta < self.minFrameSecs)):
                time.sleep(self.minFrameSecs - self.lastDelta)
                stop = ti.default_timer()
                self.lastDelta = stop - start

        self.shutdown()

        print "Client: end run"
        self.socket.close()

    def send(self, proto, data = b''):
        try:
            # if proto != Proto.str:
                # print "Proto: " + proto + " data: " + data
            if not self.socket.send(proto + data, zmq.NOBLOCK) == None:
                print "Client: socket send failed"
        except zmq.ZMQError:
            print "Client: socket send failed, disconnecting"
            self.svr_connect = False

    def parseMsg(self, msg):
        ret = True
        header = msg[0:Proto.headerlen]
        body = msg[Proto.headerlen:]
        for case in switch(header):
            if case(Proto.greet):
                print "Client: server greet"
                self.svr_connect = True
                break
            if case(Proto.str):
                print "Client: string: " + body
                break
            if case(Proto.ping):
                print "Client: server ping"
                break
            if case(Proto.serverstop):
                print "Client: serverstop"
                # Send reply to delete client
                self.svr_connect = False
                self.send(Proto.clientstop)
                ret = False
                break
            if case(Proto.clientwin):
                print "Client: clientwin"
                self.svr_connect = False
                self.send(Proto.clientstop)
                player = self.players[0]
                self.gameover(player)
                break
            if case(Proto.clientlose):
                print "Client: clientlose"
                self.svr_connect = False
                self.send(Proto.clientstop)
                player = self.players[0]
                self.gameover(player)
                break
            if case(Proto.addclient):
                split = body.split(":")
                otherid = split[0]
                print "got addclient for " + otherid
                color = sdl2.ext.Color(int(split[1]), int(split[2]), int(split[3]), 255)
                print color
                self.addPlayer(otherid, color)
                self.clientmap[otherid] = {'vx': 0, 'fire': False, 'lives': 3, 'score': 0}
                print "number of players %d" % len(self.players)
                break
            if case(Proto.removeclient):
                split = body.split(":")
                otherid = split[0]
                print "got removeclient for " + otherid
                self.removePlayer(otherid)
                del self.clientmap[otherid]
                print "number of players %d" % len(self.players)
                break
            if case(Proto.moveother):
                split = body.split(":")
                id = split[0]
                self.clientmap[id]['vx'] = float(split[1])
                break
            if case(Proto.fireother):
                id = body
                self.clientmap[id]['fire'] = True
                break
            if case(Proto.lostlife):
                split = body.split(":")
                id = split[0]
                self.clientmap[id]['lives'] = int(split[1])
                # print self.clientmap
                for player in self.players:
                    player.lives = self.clientmap[player.id]['lives']
                    self.livesUI[player.id].updateLives(player.lives)
                for bullet in self.enemycontrol.bullets:
                    self.enemycontrol.removebullet(bullet)
                break
            if case(Proto.scoreup):
                split = body.split(":")
                id = split[0]
                # update score
                player = self.players[0]
                player.score = int(split[1])
                self.clientmap[id]['score'] = player.score
                self.scoreUI[id].updateScore(player.score)
                # remove destroyed enemy
                enemyIdx = int(split[2])
                enemy = self.enemycontrol.enemies[enemyIdx]
                enemy.remove()
                self.enemycontrol.enemies.remove(enemy)
                for bullet in player.bullets:
                    player.removebullet(bullet)
                break
            if case(Proto.enemyfire):
                self.enemycontrol.shooter = int(body)
                self.enemycontrol.clientfiring = True
                break
            if case(Proto.eclocupdate):
                split = body.split(":")
                left = float(split[0])
                right = float(split[1])
                # TODO
                # self.enemycontrol.left = left
                # self.enemycontrol.right = right
                print "enemy control locupdate, l: " + str(left) + " r: " + str(right)
                break
            if case():  # default
                print "Client: received undefined message!"
                # TODO: debug
        return ret

    # -------------------------------------------------------------------------------
    def update(self, time):
        # our main game loop

        # read local inputs & events
        events = sdl2.ext.get_events()
        for event in events:
            if event.type == sdl2.SDL_QUIT:
                return False
            for player in self.players:
                if player.id == self.id:
                    player.getInput(event, self.players.index(player))

        if self.gameIsActive:
            for player in self.players:
                # print "player " + str(player.id) + " at " + str(player.x)
                if player.id != self.id:
                    player.vx = self.clientmap[player.id]['vx']
                    if self.clientmap[player.id]['fire']:
                        player.fire()
                        self.clientmap[player.id]['fire'] = False
                player.update(time)
            self.enemycontrol.clientupdate(time)
            if self.enemycontrol.clientfiring:
                self.enemycontrol.fire()
                self.enemycontrol.clientfiring = False
            for player in self.players:
                if self.enemycontrol.checkWin(player):
                    self.gameover(player)
            for enemy in self.enemycontrol.enemies:
                enemy.update(time)

            for ebullet in self.enemycontrol.bullets:
                ebullet.update(time)
                for shield in self.shields:
                    hit = collision.checkCollision(ebullet, shield)
                    if hit:
                        self.enemycontrol.removebullet(ebullet)
                        shield.hit()
                        if shield.health <= 0:
                            shield.remove()
                            self.shields.remove(shield)
                        break

            for player in self.players:
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
            if len(self.enemycontrol.enemies) < 1:
                self.enemycontrol.reset()

        return True

    # -------------------------------------------------------------------------------
    def render(self):
        # clear to black
        self.renderer.color = sdl2.ext.Color(0, 0, 0, 255)
        self.renderer.clear()

        # iterate the global draw list
        for di in draw.Drawable.drawList:
            di.render()

        # test.renderTexture(image, renderer, 0, 0)
        # present renderer results
        self.renderer.present()

    # -------------------------------------------------------------------------------
    def setup(self, localPID):
        # create window
        self.width = self.options.width
        self.height = self.options.height
        windowtitle = "Space Invaders"
        if self.options.server:
            windowtitle += " - Server"
        else:
            windowtitle += " - Client"

        self.window = sdl2.ext.Window(windowtitle, size=(self.width, self.height),
                                      position=(self.width + 64, 0))
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
        # create player object
        self.addPlayer(localPID)

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