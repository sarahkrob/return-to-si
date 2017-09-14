import drawable

class renderLives(drawable.textMaker):
    def __init__(self, lives, xpos, ypos, color):
        self.message = "Lives " + str(lives)
        self.x = xpos
        self.y = ypos
        super(renderLives, self).__init__(self.message, self.x, self.y,
                                          16, textColor=color, fontname="8-BIT WONDER.TTF")

    def updateLives(self, lives):
        self.message = "Lives " + str(lives)
        self.setText(self.message)

class renderScore(drawable.textMaker):
    def __init__(self, score, xpos, ypos, color):
        self.message = "Score " + str(score)
        self.x = xpos
        self.y = ypos
        super(renderScore, self).__init__(self.message, self.x, self.y,
                                          16, textColor=color, fontname="8-BIT WONDER.TTF")

    def updateScore(self, score):
        self.message = "Score " + str(score)
        self.setText(self.message)
