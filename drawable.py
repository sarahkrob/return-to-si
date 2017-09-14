from abc import ABCMeta, abstractmethod
from ctypes import c_int, pointer
import os
from random import randint
import sdl2.ext
import sdl2.sdlimage as sdlimage
import sdl2.sdlmixer as sdlmixer
from sdl2.sdlttf import (TTF_OpenFont, TTF_CloseFont, TTF_RenderText_Shaded, TTF_GetError, TTF_Init, TTF_Quit )

###############################################################################
class GameObject():
    __metaclass__ = ABCMeta

    @abstractmethod
    def update(self, time):
        pass
###############################################################################
class Drawable(GameObject):
    # the "static" draw list
    drawList = list()

    if (sdl2.SDL_Init(sdl2.SDL_INIT_AUDIO) < 0):
        exit(1)
    if (sdlmixer.Mix_OpenAudio(22050, sdlmixer.MIX_DEFAULT_FORMAT, 2, 1024) < 0):
        print "Mix_OpenAudio: %s\n", sdlmixer.Mix_GetError()
        exit(2);

    def __init__(self, width, height, x = 0, y = 0):
        self.height = height
        self.width = width
        self.x = x
        self.y = y
        # set a random color
        self.color = sdl2.ext.Color(randint(0, 255), randint(0, 255), randint(0, 255), 255)
        # add to global drawList
        Drawable.drawList.append(self)

    # on class instance destroy, remove from drawList
    def delete(self):
        # print "removing from drawlist"
        Drawable.drawList.remove(self)

    # force clear drawList contents
    @staticmethod
    def clearAll():
        del Drawable.drawList[:]

    def update(self, time):
        pass

    def getWidth(self):
        pass

    def getHeight(self):
        pass

    def getX(self):
        pass

    def getY(self):
        pass
###############################################################################
class filledRect(Drawable):
    renderer = None

    @staticmethod
    def setRenderer(rdr):
        if isinstance(rdr, sdl2.ext.Renderer):
            filledRect.renderer = rdr
        else:
            raise TypeError("unsupported renderer type")

    def __init__(self, width, height, x = 0, y = 0,
                 color = sdl2.ext.Color(randint(0, 255), randint(0, 255), randint(0, 255), 255)):
        self.height = height
        self.width = width
        self.x = x
        self.y = y
        self.color = color
        # add to global drawList
        Drawable.drawList.append(self)

    def update(self, time):
        pass

    def render(self):
        filledRect.renderer.color = self.color
        # for now, we're only drawing filled rectangles. we can specialize this function as necessary
        # draw_rect will draw outline only, fill fills them in
        filledRect.renderer.fill([(self.x, self.y, self.width, self.height)])

    def getHeight(self):
        return self.height

    def getWidth(self):
        return self.width

    def getX(self):
        return self.x

    def getY(self):
        return self.y
###############################################################################
class spriteMaker(Drawable):
    renderer = None

    @staticmethod
    def setRenderer(rdr):
        if isinstance(rdr, sdl2.ext.Renderer):
            spriteMaker.renderer = rdr.renderer
        elif isinstance(rdr, sdl2.render.SDL_Renderer):
            spriteMaker.renderer = rdr
        else:
            raise TypeError("unsupported renderer type")

    def __init__(self, x, y, w, h, imagename, dupetexture, useimagesize=False,
                 colormod=sdl2.ext.Color(255, 255, 255, 255)):
        if imagename == '' and dupetexture is None:
            raise sdl2.ext.SDLError()

        if dupetexture is not None:
            self.texture = dupetexture
        else:
            fullpath = os.path.join(os.path.dirname(__file__), 'resources/images', imagename)
            self.texture = self._createTexture(fullpath)
        if self.texture is None:
            raise sdl2.ext.SDLError()
        sdl2.SDL_SetTextureColorMod(self.texture, colormod.r, colormod.g, colormod.b)

        self.x = x
        self.y = y
        if useimagesize:
            # reset size if using image dimensions
            pw = pointer(c_int(0))
            ph = pointer(c_int(0))
            sdl2.SDL_QueryTexture(self.texture, None, None, pw, ph)
            self.width = pw.contents.value
            self.height = ph.contents.value
        else:
            self.width = w
            self.height = h

        Drawable.drawList.append(self)

    def _createTexture(self, fullpath):
        surface = sdlimage.IMG_Load(fullpath)
        if surface is None:
            raise sdlimage.IMG_GetError()
        texture = sdl2.render.SDL_CreateTextureFromSurface(spriteMaker.renderer, surface)
        if texture is None:
            raise sdl2.ext.SDLError()
        sdl2.surface.SDL_FreeSurface(surface)
        return texture

    def render(self):
        dst = sdl2.SDL_Rect(self.x, self.y, self.width, self.height)
        sdl2.SDL_RenderCopy(spriteMaker.renderer, self.texture, None, dst)

    def getHeight(self):
        return self.height

    def getWidth(self):
        return self.width

    def getX(self):
        return self.x

    def getY(self):
        return self.y
###############################################################################
class textMaker(GameObject):
    renderer = None

    @staticmethod
    def setRenderer(rdr):
        if isinstance(rdr, sdl2.ext.Renderer):
            textMaker.renderer = rdr.renderer
        elif isinstance(rdr, sdl2.render.SDL_Renderer):
            textMaker.renderer = rdr
        else:
            raise TypeError("unsupported renderer type")

    def __init__(self, text = "", xpos = 0, ypos = 0, fontSize = 24,
                 textColor = sdl2.ext.Color(255, 255, 255),
                 bgColor = sdl2.ext.Color(0, 0, 0), fontname = "Arial.ttf"):
        # to make fonts work, create a folder in the same folder as this script called 'font'
        # this font can be downloaded from: http://www.glukfonts.pl/font.php?font=Glametrix
        #  font = os.path.join(os.path.dirname(__file__), 'font', 'Glametrix.otf')
        # this font is just copied from your Mac in /Library/fonts/Arial.ttf to the 'font' folder
        TTF_Init()

        if fontname == "":
            raise TTF_GetError()

        font = os.path.join(os.path.dirname(__file__), 'resources/fonts', fontname)
        self.font = TTF_OpenFont(font, fontSize)
        if self.font is None:
            raise TTF_GetError()
        self._text = text
        self.x = xpos
        self.y = ypos
        self.fontSize = fontSize
        self.textColor = sdl2.pixels.SDL_Color(textColor.r, textColor.g, textColor.b, textColor.a)
        self.backgroundColor = sdl2.pixels.SDL_Color(bgColor.r, bgColor.g, bgColor.b, bgColor.a)
        self.texture = self._createTexture()
        Drawable.drawList.append(self)
        # TODO
        # I'm not sure if Sarah added this or if it was original code, but closing the font
        # at the end of the init means subsequent updateTexture calls will fail. It seems more
        # logical to keep the font open for the duration of the instance lifetime. That said,
        # at some point we need to ensure we are cleaning up properly
        # TTF_CloseFont(self.font)

    # on class instance destroy, remove from drawList
    def delete(self):
        # print "removing from drawlist"
        Drawable.drawList.remove(self)

    def _createTexture(self):
        textSurface = TTF_RenderText_Shaded(self.font, self._text, self.textColor, self.backgroundColor)
        if textSurface is None:
            raise TTF_GetError()
        texture = sdl2.render.SDL_CreateTextureFromSurface(textMaker.renderer, textSurface)
        if texture is None:
            raise sdl2.ext.SDLError()
        sdl2.surface.SDL_FreeSurface(textSurface)
        return texture

    def _updateTexture(self):
        textureToDelete = self.texture
        self.texture = self._createTexture()
        sdl2.render.SDL_DestroyTexture(textureToDelete)

    def render(self):
        dst = sdl2.SDL_Rect(self.x, self.y)
        w = pointer(c_int(0))
        h = pointer(c_int(0))
        sdl2.SDL_QueryTexture(self.texture, None, None, w, h)
        dst.w = w.contents.value
        dst.h = h.contents.value
        sdl2.SDL_RenderCopy(textMaker.renderer, self.texture, None, dst)

    def getText(self):
        return self._text

    def setText(self, value):
        if self._text == value:
            return
        self._text = value
        self._updateTexture()

    def update(self, time):
        pass
###############################################################################
