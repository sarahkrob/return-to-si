import os
from random import randint
import sdl2
import sdl2.sdlmixer as sdlmixer
import drawable as draw
import localmath as lm

class Player(draw.spriteMaker):

    def __init__(self, wwidth, wheight, id, posx, posy, width, height, color):
        playerwidth, playerheight = lm.SC(width, height)
        playerposx, playerposy = lm.NDCToSC(posx, posy, wwidth, wheight)
        playerposx -= playerheight + playerheight / 2
        playerposy -= playerheight + 10
        self.colormod = color
        super(Player, self).__init__(int(playerposx), int(playerposy), int(playerwidth), int(playerheight),
                                     "ship.png", None, False, self.colormod)
        Player.width = playerwidth
        Player.height = playerheight
        Player.maxwidth = wwidth
        Player.maxheight = wheight
        self.bulletcount = 0
        path = os.path.join(os.path.dirname(__file__), 'resources/sounds', 'shoot.wav')
        Player.shootsound = sdlmixer.Mix_LoadWAV(path)
        path = os.path.join(os.path.dirname(__file__), 'resources/sounds', 'explosion.wav')
        Player.hitsound = sdlmixer.Mix_LoadWAV(path)
        self.vx = 0
        self.id = id
        self.bullets = list()
        self.lives = 3
        self.score = 0
        # states set by messages
        self.move = False
        self.shoot = False

    def remove(self):
        for bullet in self.bullets:
            bullet.remove()
        self.delete()

    def fire(self):
        for bullet in self.bullets:
            if bullet.y < -16:
                self.bullets.remove(bullet)
        if self.bulletcount >= .5:
            self.bullets.append(Bullet(int(self.x + self.width / 2),
                                       self.y, self.maxwidth, self.maxheight, self.colormod))
            sdlmixer.Mix_PlayChannel(-1, self.shootsound, 0)
            self.bulletcount = 0

    def getInput(self, event, number):
        if sdl2.SDL_HasScreenKeyboardSupport:
            self.move = False
            oldvx = self.vx
            if event.type == sdl2.SDL_KEYDOWN:
                if event.key.keysym.sym == sdl2.SDLK_LEFT:
                    self.vx = -.75
                if event.key.keysym.sym == sdl2.SDLK_RIGHT:
                    self.vx = .75
                if event.key.keysym.sym == sdl2.SDLK_SPACE:
                    self.shoot = True
                    self.fire()
            elif event.type == sdl2.SDL_KEYUP:
                if event.key.keysym.sym in (sdl2.SDLK_LEFT, sdl2.SDLK_RIGHT):
                    self.vx = 0
            if oldvx != self.vx:
                self.move = True

    def lostlife(self):
        sdlmixer.Mix_PlayChannel(-1, self.hitsound, 0)
        self.lives -= 1

    def update(self, time):
        self.bulletcount += time
        # width and height of sprite so it can stay in bounds
        swidth, sheight = self.width, self.height
        # move sprite
        self.x += lm.NDCToSC_x(self.vx * time, self.maxwidth)
        # checks if sprite is past the min (0)
        self.x = max(0, self.x)
        # position + sprite size
        posx = self.x + swidth
        # if the position + sprite size extends past max, stop it there
        if posx > self.maxwidth:
            self.x = self.maxwidth - swidth

    def removebullet(self, bullet):
        bullet.remove()
        self.bullets.remove(bullet)

class Bullet(draw.filledRect):
    def __init__(self, posx, posy, wwidth, wheight, color):
        bulletwidth, bulletheight = lm.NDCToSC(.01, .025, wwidth, wheight)
        super(Bullet, self).__init__(int(bulletwidth), int(bulletheight), color=color)
        self.x = posx
        self.y = posy
        Bullet.maxheight = wheight
        Bullet.vy = -.5

    def update(self, time):
        self.y += lm.NDCToSC_y(self.vy * time, self.maxheight)

    def remove(self):
        self.delete()

class Enemy(draw.spriteMaker):
    def __init__(self, points, speed, wwidth, wheight, posx=0.0, posy=0.0, width=0.0, height=0.0):
        enemywidth, enemyheight = lm.NDCToSC(width, height, wwidth, wheight)
        enemyposx, enemyposy = lm.NDCToSC(posx, posy, wwidth, wheight)
        name = "enemy" + str(points/10) + ".png"
        super(Enemy, self).__init__(int(enemyposx), int(enemyposy), int(enemywidth), int(enemyheight),
                                    name, None, False)
        self.points = points
        Enemy.width = enemywidth
        Enemy.height = enemyheight
        Enemy.maxwidth = wwidth - lm.NDCToSC_x(.05, wwidth)
        Enemy.minwidth = lm.NDCToSC_x(.05, wwidth)
        Enemy.maxheight = wheight
        Enemy.vx = speed
        Enemy.vy = 0
        Enemy.move = True
        path = os.path.join(os.path.dirname(__file__), 'resources/sounds', 'invaderkilled.wav')
        Enemy.deathsound = sdlmixer.Mix_LoadWAV(path)

    def update(self, time):
        self.y += lm.NDCToSC_y(Enemy.vy * time, self.maxheight)
        if self.move:
            self.x += lm.NDCToSC_x(Enemy.vx * time, self.maxwidth)

    def shoot(self):
        for bullet in EnemyController.bullets:
            if bullet.y > self.maxheight:
                EnemyController.removebullet(bullet)
        if len(EnemyController.bullets) < 1:
            EnemyController.bullets.append(EnemyBullet(int(self.x + self.width / 2),
                                            self.y, self.maxwidth, self.maxheight))

    def remove(self):
        sdlmixer.Mix_PlayChannel(-1, self.deathsound, 0)
        self.delete()

class EnemyController(draw.GameObject):
    def __init__(self, wwidth, wheight):
        EnemyController.level = 1
        EnemyController.enemies = self.createEnemies(wwidth, wheight)
        EnemyController.shooter = 0
        EnemyController.serverfiring = False
        EnemyController.clientfiring = False
        EnemyController.top = self.enemies[0].y
        EnemyController.left = self.enemies[0].x
        EnemyController.right = self.enemies[-1].x + self.enemies[-1].width
        EnemyController.bottom = self.enemies[-1].y + self.enemies[-1].height
        EnemyController.wwidth = wwidth
        EnemyController.wheight = wheight
        EnemyController.counter = 0
        EnemyController.timer = 0
        EnemyController.bullets = list()
        EnemyController.shoottime = randint(90, 100)
        EnemyController.UFOactive = False
        EnemyController.UFOtime = randint(12, 15)
        EnemyController.UFOcounter = 0
        path = os.path.join(os.path.dirname(__file__), 'resources/sounds', 'fastinvader4.wav')
        EnemyController.sound = sdlmixer.Mix_LoadWAV(path)
        path = os.path.join(os.path.dirname(__file__), 'resources/sounds', 'levup.wav')
        EnemyController.resetsound = sdlmixer.Mix_LoadWAV(path)

    def createEnemies(self, wwidth, wheight):
        enemies = list()
        yoffset = .06
        xoffset = .09
        scorecountdown = 15
        points = 40
        speed = .25 * self.level
        y = .125
        while y < .45:
            x = .1
            while x < .85:
                if scorecountdown == 0 and not points == 10:
                    points -= 10
                    scorecountdown = 15
                enemy = Enemy(points, speed, wwidth, wheight, x, y, 0.072, 0.05)
                enemies.append(enemy)
                scorecountdown -= 1
                x += xoffset
            y += yoffset
        return enemies

    def update(self, time):
        pass

    def serverupdate(self, time):
        Enemy.vy = 0
        if Enemy.move:
            distancemoved = lm.NDCToSC_x(Enemy.vx * time, self.wwidth)
        else:
            distancemoved = 0
        EnemyController.left += distancemoved
        EnemyController.right += distancemoved
        if EnemyController.right > Enemy.maxwidth or EnemyController.left < Enemy.minwidth:
            Enemy.vx = -Enemy.vx
            Enemy.vy = .5
            EnemyController.counter = 15
        if EnemyController.timer == self.shoottime:
            self.serverfiring = True
            self.shooter = randint(0, len(self.enemies) - 1)
            self.enemies[self.shooter].shoot()
            EnemyController.timer = 0
        if EnemyController.UFOcounter >= self.UFOtime and not EnemyController.UFOactive:
            ufo = UFO(self.wwidth, self.wheight)
            EnemyController.UFOactive = True
            EnemyController.UFOcounter = 0
            EnemyController.enemies.append(ufo)
        if EnemyController.counter >= .75:
            Enemy.move = True
            sdlmixer.Mix_PlayChannel(-1, self.sound, 0)
            EnemyController.counter = 0
        else:
            Enemy.move = False
            EnemyController.counter += time
        EnemyController.timer += 1
        EnemyController.UFOcounter += time

    def clientupdate(self, time):
        Enemy.vy = 0
        if Enemy.move:
            distancemoved = lm.NDCToSC_x(Enemy.vx * time, self.wwidth)
        else:
            distancemoved = 0
        EnemyController.left += distancemoved
        EnemyController.right += distancemoved
        if EnemyController.right > Enemy.maxwidth or EnemyController.left < Enemy.minwidth:
            Enemy.vx = -Enemy.vx
            Enemy.vy = .5
            EnemyController.counter = 15
        if EnemyController.UFOcounter >= self.UFOtime and not EnemyController.UFOactive:
            ufo = UFO(self.wwidth, self.wheight)
            EnemyController.UFOactive = True
            EnemyController.UFOcounter = 0
            EnemyController.enemies.append(ufo)
        if EnemyController.counter >= .75:
            Enemy.move = True
            sdlmixer.Mix_PlayChannel(-1, self.sound, 0)
            EnemyController.counter = 0
        else:
            Enemy.move = False
            EnemyController.counter += time
        EnemyController.timer += 1
        EnemyController.UFOcounter += time

    def fire(self):
        self.enemies[self.shooter].shoot()
        EnemyController.timer = 0

    def checkWin(self, player):
        enemyheight = self.enemies[-1].y + self.enemies[0].height
        if enemyheight >= player.y:
            return True
        else:
            return False

    @staticmethod
    def removebullet(bullet):
        bullet.remove()
        EnemyController.bullets.remove(bullet)

    def reset(self):
        EnemyController.level += .8
        del self.enemies[:]
        EnemyController.enemies = self.createEnemies(self.wwidth, self.wheight)
        EnemyController.top = self.enemies[0].y
        EnemyController.left = self.enemies[0].x
        EnemyController.right = self.enemies[-1].x + self.enemies[-1].width
        EnemyController.bottom = self.enemies[-1].y + self.enemies[-1].height
        sdlmixer.Mix_PlayChannel(-1, self.resetsound, 0)

class UFO(draw.spriteMaker):
    def __init__(self, wwidth, wheight):
        enemywidth, enemyheight = lm.NDCToSC(.108, .05, wwidth, wheight)
        ypos = lm.NDCToSC_y(.075, wheight)
        pickside = randint(0, 1)
        if pickside == 0:
            UFO.vx = -0.25
            xpos = lm.NDCToSC_x(1, wwidth)
        if pickside == 1:
            UFO.vx = 0.25
            xpos = 0
        super(UFO, self).__init__(int(xpos), int(ypos), int(enemywidth), int(enemyheight),
                                                                 "enemy5.png", None, False)
        UFO.points = 100
        UFO.width = self.width
        if pickside == 1:
            self.x = -self.width
        path = os.path.join(os.path.dirname(__file__), 'resources/sounds', 'ufo_lowpitch.wav')
        UFO.sound = sdlmixer.Mix_LoadWAV(path)
        sdlmixer.Mix_PlayChannel(-1, self.sound, 0)

    def remove(self):
        EnemyController.UFOactive = False
        self.delete()

    def shoot(self):
        pass

    def update(self, time):
        self.x += lm.NDCToSC_x(UFO.vx * time, Enemy.maxwidth)
        if UFO.vx < 0 and self.x < -UFO.width:
            self.delete()
            EnemyController.enemies.remove(self)
            EnemyController.UFOactive = False
        elif UFO.vx > 0 and self.x > Enemy.maxwidth:
            self.delete()
            EnemyController.enemies.remove(self)
            EnemyController.UFOactive = False

class EnemyBullet(draw.filledRect):
    def __init__(self, posx, posy, wwidth, wheight):
        bulletwidth, bulletheight = lm.NDCToSC(.01, .025, wwidth, wheight)
        super(EnemyBullet, self).__init__(int(bulletwidth), int(bulletheight),
                                          color=sdl2.ext.Color(255, 255, 255, 255))
        self.x = posx
        self.y = posy
        EnemyBullet.height = bulletheight
        EnemyBullet.maxheight = wheight
        EnemyBullet.vy = .5

    def update(self, time):
        self.y += lm.NDCToSC_y(self.vy * time, self.maxheight)

    def remove(self):
        self.delete()

class Shield(draw.spriteMaker):
    def __init__(self, posx, posy, wwidth, wheight):
        self.shieldwidth, self.shieldheight = lm.NDCToSC(.135, .08, wwidth, wheight)
        self.shieldposx, self.shieldposy = lm.NDCToSC(posx, posy, wwidth, wheight)
        Shield.health = 6
        super(Shield, self).__init__(int(self.shieldposx), int(self.shieldposy), int(self.shieldwidth),
                                     int(self.shieldheight), "shield6.png", None, False)

    def hit(self):
        self.health -= 1
        name = "shield" + str(self.health) + ".png"
        super(Shield, self).__init__(int(self.shieldposx), int(self.shieldposy), int(self.shieldwidth), int(self.shieldheight),
                                     name, None, False)

    def remove(self):
        self.delete()