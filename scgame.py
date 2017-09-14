from options import Options
from random import randint
import sdl2.ext
import drawable as draw
import collision
import ui
import scgameobjects as scgo
import localmath

class scgame(object):
    def __init__(self):
        self.gameIsActive = True
        self.width = 0
        self.height = 0
        self.renderer = None
        self.window = None
        self.players = list()
        self.enemycontrol = None
        self.shields = list()
        self.livesUI = dict()
        self.scoreUI = dict()
        self.fpsCounter = None
        self.limitFrame = None
        self.options = Options().opts
        self.minFrameSecs = None
        self.lastDelta = 0
        self.move = False

    # -------------------------------------------------------------------------------
    def addPlayer(self, id, color=sdl2.ext.Color(randint(0, 255), randint(0, 255), randint(0, 255), 255)):
        # print "adding player"
        player = scgo.Player(self.width, self.height, id, 0.5, 1.0, 66, 28.8, color)
        self.players.append(player)
        height = localmath.NDCToSC_y(.015, self.height) * len(self.players)
        self.livesUI[id] = ui.renderLives(player.lives, 5, height, color)
        self.scoreUI[id] = ui.renderScore(player.score, self.width - (self.width / 3) - 25, height, color)

    # -------------------------------------------------------------------------------
    def removePlayer(self, id):
        for player in self.players:
            if player.id == id:
                player.remove()
                self.players.remove(player)
                if id in self.livesUI:
                    self.livesUI[id].delete()
                    del self.livesUI[id]
                if id in self.scoreUI:
                    self.scoreUI[id].delete()
                    del self.scoreUI[id]
            # print "removing player"

    # -------------------------------------------------------------------------------
    def clear(self):
        print "clearing"
        self.renderer.color = sdl2.ext.Color(0, 0, 0, 255)
        self.renderer.clear()
        self.renderer.present()

    # -------------------------------------------------------------------------------
    def gameover(self, player):
        # Empty the current drawlist
        draw.Drawable.clearAll()
        # Add ONLY the gameover text
        draw.textMaker("GAME OVER", self.width / 5, (self.height / 2) - 50, 40,
                       fontname="8-BIT WONDER.TTF")
        text = "SCORE " + str(player.score)
        draw.textMaker(text, self.width / 5, (self.height / 2), 30,
                       fontname="8-BIT WONDER.TTF")
        # Signal update function to end
        self.gameIsActive = False

    # -------------------------------------------------------------------------------
    def update(self, time):
        # our main game loop

        # read local inputs & events
        events = sdl2.ext.get_events()
        for event in events:
            if event.type == sdl2.SDL_QUIT:
                return False
                break
            for player in self.players:
                player.getInput(event, self.players.index(player))
        if self.gameIsActive:

            for player in self.players:
                # print "player " + str(player.id) + " at " + str(player.x)
                player.update(time)
            self.enemycontrol.serverupdate(time)
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
                    hit = collision.checkCollision(ebullet, player)
                    if hit:
                        # print "enemy hit"
                        self.enemycontrol.removebullet(ebullet)
                        player.lostlife()
                        self.livesUI[player.id].updateLives(player.lives)
                        if player.lives <= 0:
                            self.gameover(player)
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
                    for enemy in self.enemycontrol.enemies:
                        hit = collision.checkCollision(bullet, enemy)
                        if hit:
                            player.score += enemy.points
                            self.scoreUI[player.id].updateScore(player.score)
                            enemy.remove()
                            self.enemycontrol.enemies.remove(enemy)
                            player.removebullet(bullet)
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

    def shutdown(self):
        pass
