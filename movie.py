from PyQt5.QtCore import pyqtSignal, QThread, Qt, QRectF, QPointF
from PyQt5.QtGui import QTransform, QPen, QFont
from PyQt5.QtWidgets import *

from astropy.coordinates import SkyCoord
import astropy.units as u

import pyqtgraph as pg
from widgets import *
import numpy as np
import time, util, resources, math

class Movie(pg.GraphicsView):

    #required parameters
    player = None
    maps = []
    moviePlayerQTParent = None
    
    #properties
    type = "cea"
    imgs = []
    views = []
    clim = 1000
    scale = 4096
    
    #button states
    crop = False
    track = True

    #temporary
    rect = None
    rectStart = [None, None]
    pos = None

    def __init__(self, **kwargs): 
        super().__init__(useOpenGL=True)

        for key, value in kwargs.items():
            setattr(self, key, value)
        self.player.updateIdx.connect(self.updateImage)

        self.imgs = self.maps.getData(self.type + str(self.scale))

        self.ci = pg.GraphicsLayout()
        self.setCentralItem(self.ci)

        self.plot = self.ci.addPlot(title="") 
        #self.plot.setMouseEnabled(x=False, y=False)
        self.plot.setMenuEnabled(enableMenu=False)
        self.plot.scene().sigMouseClicked.connect(self.mouseClick)
        self.plot.scene().sigMouseMoved.connect(self.mouseMove)

        self.img = pg.ImageItem()
        self.img.setLevels([-self.clim, self.clim])
        self.img.setImage(self.imgs[0])
        if self.type == 'hpc':
            self.img.setRect(QRectF(-1024, -1024, 2048, 2048))
            self.plot.setAspectLocked()
            name = 'Helioprojective'
            unit = 'arcseconds'
        else:
            h = 4096
            self.img.setRect(QRectF(-180, 0, 360, h))
            majorticks = []
            ticks = []
            minorticks = []
            for phi in range(-90, 91):
                if phi%30 == 0 or (abs(phi) <= 50 and phi%10 == 0):
                    majorticks.append((h/2*math.sin(math.radians(phi)) + h/2, str(phi)))
                elif phi%10 == 0:
                    ticks.append((h/2*math.sin(math.radians(phi)) + h/2, str(phi)))
                else:
                    minorticks.append((h/2*math.sin(math.radians(phi)) + h/2, str(phi)))
            self.plot.getAxis('left').setTicks([majorticks, ticks, minorticks])
            self.plot.setAspectLocked(lock=True, ratio=np.pi*4096/360)
            name = 'Heliographic'
            unit = "degrees"
        self.plot.getAxis('left').setLabel(text=f"{name} Latitude", units=unit)
        self.plot.getAxis('left').enableAutoSIPrefix(enable=False)
        self.plot.getAxis('bottom').setLabel(text=f"{name} Longitude", units=unit)
        self.plot.getAxis('bottom').enableAutoSIPrefix(enable=False)
        self.setViewBox()
        self.plot.addItem(self.img)

    def updateImage(self, i):
        self.img.setImage(self.imgs[i])
        self.img.setLevels([-self.clim, self.clim])
        self.plot.getViewBox().setRange(self.views[i])
        self.img.setRect(self.views[i])
        self.mouseMove(self.pos)

    def mouseClick(self, event):
        if self.rect is None and self.crop:
            self.rect = QGraphicsRectItem(event.scenePos().x(), event.scenePos().y(), 0, 0)
            pen = QPen(Qt.white)
            self.rect.setPen(pen)
            self.plot.scene().addItem(self.rect)
            self.rectStart = event.scenePos()
            self.moviePlayerQTParent.pb.toggle(None, state=True)

        elif self.rect is not None:
            self.plot.scene().removeItem(self.rect)
            coords = [self.plot.getViewBox().mapSceneToView(event.scenePos()), self.plot.getViewBox().mapSceneToView(self.rectStart)]
            x = min(coords[0].x(), coords[1].x())
            y = min(coords[0].y(), coords[1].y())
            w = abs(coords[0].x() - coords[1].x())
            h = abs(coords[0].y() - coords[1].y())
            self.setViewBox(QRectF(x, y, w, h))
            self.rect = None
            self.moviePlayerQTParent.changezoom.emit()
            self.crop = False

    def mouseMove(self, pos):
        if pos is None:
            return

        if self.rect is not None and pos is not None:
            self.rect.setRect(QRectF(min(self.rectStart.x(), pos.x()), min(self.rectStart.y(), pos.y()), abs(self.rectStart.x() - pos.x()), abs(self.rectStart.y() - pos.y())))
        elif self.rect is not None and not self.crop:
            self.plot.scene().removeItem(self.rect)
            self.rect = None

        self.pos = pos
        pos = self.plot.getViewBox().mapSceneToView(pos)
        if self.type == "hpc":
            x = pos.x()*u.arcsec
            y = pos.y()*u.arcsec
        else:
            x = pos.x()*u.deg
            try:
                y = math.asin(pos.y()/2048 - 1)*u.rad
                y = y.to("deg")
            except ValueError:
                y = "---"
        try:
            coords = SkyCoord(x, y, frame=self.maps[self.type + str(self.scale)][self.player.i].coordinate_frame)
            x, y = self.maps[self.type + str(self.scale)][self.player.i].world_to_pixel(coords)
            # print(x.value, y.value)
            try: 
                value = self.maps[self.type + str(self.scale)][self.player.i].data[int(y.value + 0.5)][int(x.value + 0.5)]
                if value is not None and not math.isnan(value):
                    v = "%07.3fG" % (float(value/((4096/self.scale)**2)))
                else:
                    v = " ---.---G"
            except IndexError:
                v = " ---.---G"
        except ValueError:
            v = " ---.---G"
        
        if self.type == "hpc":
            self.moviePlayerQTParent.pointerupdate.emit(['''%04d"''' % (pos.x()), '''%04d"''' % (pos.y()), v])
        else:
            try:
                y = '''%02d°''' % (int(math.degrees(math.asin(pos.y()/2048 - 1)) + 0.5))
            except ValueError:
                y = '---'
            self.moviePlayerQTParent.pointerupdate.emit(['''%03d°''' % (pos.x()), y, v])

    def setViewBox(self, frame=None):
        print(frame)
        if frame is None:
            if self.type == "hpc":
                self.views = [QRectF(-1024, -1024, 2048, 2048)] * len(self.imgs)
            else:
                self.views = [QRectF(-180, 0, 360, 4096)] * len(self.imgs)
        elif not self.track:
            self.views = [frame] * len(self.imgs)
        else: 
            tl = frame.topLeft()
            br = frame.bottomRight()
            w = abs(tl.x() - br.x())
            if self.type == 'hpc':
                h = abs(tl.y() - br.y())
                x = (tl.x() + br.x())/2*u.arcsec
                y = (tl.y() + br.y())/2*u.arcsec
            else:
                h = (abs(math.degrees(math.asin((tl.y())/2048 - 1)) - math.degrees(math.asin(br.y()/2048 - 1)))) #width in degrees
                h2 = abs(tl.y() - br.y()) #width in arbitrary coordinates
                y = (math.degrees(math.asin((tl.y()+br.y())/4096 - 1)))*u.deg #center by pixel
                x = (tl.x() + br.x())/2*u.deg
                # print((math.degrees(math.asin(tl.y()/2048 - 1)) + math.degrees(math.asin(br.y()/2048 - 1)))/2)
                # print(x, y)
            center = SkyCoord(x, y, frame=self.maps[self.type + str(self.scale)][self.player.i].coordinate_frame)
            for i in range(len(self.maps)):
                c = util.rotate(self.maps[self.type + str(self.scale)][self.player.i], center, (self.maps[self.type + str(self.scale)][i].date - self.maps[self.type + str(self.scale)][self.player.i].date).to(u.day), type=self.type)
                if self.type == 'hpc':
                    self.views[i] = QRectF(c.Tx.arcsec - w/2, c.Ty.arcsec - h/2, w, h)
                else:
                    self.views[i] = QRectF(c.lon.degree - w/2, (math.sin(math.radians(c.lat.degree)) + 1)*2048 - h2/2, w, h2)

        # print(self.views[0].topLeft().x(), self.views[0].topLeft().y(), self.views[0].bottomRight().x(), self.views[0].bottomRight().y())
        self.imgs, self.scale = self.maps.crop(self.views, self.type)
        self.updateImage(self.player.i)

class Player(QThread): #used to control all frame changes in Movie class(es) - all instances of Movie should be connected to one player

    updateIdx = pyqtSignal(int)
    updateSlider = pyqtSignal(int)
    reverseSignal = pyqtSignal(bool)

    speed = 0.1

    i = 0
    fp = 0 #front pointer
    bp = 0 #back pointer

    paused = True
    reverse = False
    rock = False

    def __init__(self, size):
        self.bp = size
        super().__init__()

    def run(self):
        while True:
            while self.paused:
                time.sleep(0.1)
            self.inc()
            time.sleep(self.speed)

    def inc(self):
        if self.reverse: self.i -= 1
        else: self.i += 1
        if self.rock and self.i >= self.bp:
            self.i -= 2
            self.reverse = (not self.reverse)
            self.reverseSignal.emit(True)
        elif self.rock and self.i < self.fp:
            self.i += 2
            self.reverse = (not self.reverse)
            self.reverseSignal.emit(False)
        else: self.i = self.fp + (self.i - self.fp) % (self.bp - self.fp)
        self.updateIdx.emit(self.i)
        self.updateSlider.emit(self.i)

    def set(self, i):
        self.i = i
        self.updateIdx.emit(i)

class MList(dict):
    def __init__(self, maps):
        super().__init__()
        self['hpc4096'] = maps
        self['hpc2048'] = [m.superpixel([2, 2]*u.pix) for m in self['hpc4096']]
        self['hpc1024'] = [m.superpixel([2, 2]*u.pix) for m in self['hpc2048']]

    def __len__(self):
        return len(self['hpc4096'])
        
    def getData(self, idx):
        if idx[:3] == 'hpc':
            return [np.flip(np.rot90(m.data), axis=1)/((4096/int(idx[3:]))**2) for m in self[idx]]
        if idx[:3] == 'cea':
            if 'cea4096' not in self:
                self.genCEA()
            return [np.flip(np.rot90(m.data), axis=0)/((4096/int(idx[3:]))**2) for m in self[idx]]

    def genCEA(self):
        self['cea4096'] = [util.reproject_cea(m) for m in self['hpc4096']]
        self['cea2048'] = [m.superpixel([2, 2]*u.pix) for m in self['cea4096']]

    def crop(self, views, type):
		# TODO: do not let crop dimensions exceed array bounds
        ans = []

        if type == 'hpc':
            for i, view in enumerate(views):
                topLeft = view.topLeft()
                bottomRight = view.bottomRight()
                sl = max(bottomRight.x() - topLeft.x(), topLeft.y(), - bottomRight.y())
                if sl < 512:
                    scale = 4096
                elif sl < 1024:
                    scale = 2048
                else:
                    scale = 1024
                x1 = int(util.scale(topLeft.x(), (-1024, 1024), (0, scale)) + 0.5)
                y1 = int(util.scale(topLeft.y(), (-1024, 1024), (0, scale)) + 0.5)
                x2 = int(util.scale(bottomRight.x(), (-1024, 1024), (0, scale)) + 0.5)
                y2 = int(util.scale(bottomRight.y(), (-1024, 1024), (0, scale)) + 0.5)
                ans.append(np.flip(np.rot90(self[type + str(scale)][i].data), axis=1)[x1:x2,y1:y2]/((4096/scale)**2))
                #print(np.flip(np.rot90(self['hpc' + str(scale)][i].data), axis=1)[x1:x2,y1:y2].shape)
        else:
            for i, view in enumerate(views):
                topLeft = view.topLeft()
                bottomRight = view.bottomRight()
                sl = max((bottomRight.x() - topLeft.x())*2048/360, (bottomRight.y() - topLeft.y())/2)
                if sl < 768:
                    scale = 4096
                else:
                    scale = 2048
                x1 = int(util.scale(topLeft.x(), (-180, 180), (0, scale)) + 0.5)
                y1 = int(util.scale(topLeft.y(), (0, 4096), (0, len(self['cea' + str(scale)][0].data))) + 0.5)
                x2 = int(util.scale(bottomRight.x(), (-180, 180), (0, scale)) + 0.5)
                y2 = int(util.scale(bottomRight.y(), (0, 4096), (0, len(self['cea' + str(scale)][0].data))) + 0.5)
                # print(x1, x2, y1, y2)
                ans.append(np.flip(np.rot90(self[type + str(scale)][i].data), axis=0)[x1:x2,y1:y2]/((4096/scale)**2)) 
        return ans, scale

class MoviePlayerQT(QWidget):

    size = 0
    widgets = 0

    changezoom = pyqtSignal()
    pointerupdate = pyqtSignal(list)

    def __init__(self, maps, **kwargs):
        super().__init__(**kwargs)
        self.size = len(maps)

        if not isinstance(maps, MList):
            self.maps = MList(maps)
        else:
            self.maps = maps

        self.mainlayout = QVBoxLayout(self)
        self.controlwidget = QWidget()
        self.controllayout = QGridLayout(self.controlwidget)
        self.setStyleSheet("QObject { background: #404040 }")
        self.mainlayout.addWidget(self.controlwidget)

        self.player = Player(self.size)
        self.start = self.player.start

        self.movie = [[Movie(maps=self.maps, player=self.player, scale=4096, moviePlayerQTParent=self)]]
        self.moviewidget = QWidget()
        self.movielayout = QGridLayout(self.moviewidget)
        self.controllayout.addWidget(self.moviewidget, 0, 0, 1, -1)
        for i, row in enumerate(self.movie):
            for j, movie in enumerate(row):
                self.movielayout.addWidget(movie, i, j)

        self.loadControls()
        self.player.start()

    def loadControls(self):
        #play/pause button
        self.pb = PlayButton()
        self.pb.toggled.connect(lambda state: setattr(self.player, 'paused', state))
        self.addWidget(self.pb)
        self.pb.setToolTip("Play/Pause")

        #back button
        self.bb = Button(icon=QIcon(':/movie-player/back.png'))
        self.bb.clicked.connect(lambda _: self.step((self.player.i - 1)%self.size))
        self.addWidget(self.bb)
        self.bb.setToolTip("Back")

        #forward button
        self.fb = Button(icon=QIcon(':/movie-player/forward.png'))
        self.fb.clicked.connect(lambda _: self.step((self.player.i + 1)%self.size))
        self.addWidget(self.fb)
        self.fb.setToolTip("Forward")

        #reverse button
        self.rb = Button(icon=QIcon(':/movie-player/reverse.png'))
        self.rb.setCheckable(True)
        self.rb.clicked.connect(lambda _: setattr(self.player, 'reverse', self.rb.isChecked()))
        self.player.reverseSignal.connect(lambda val: self.rb.setChecked(val))
        self.addWidget(self.rb)
        self.rb.setToolTip("Play in Reverse")

        #rock button
        self.rlb = Button(icon=QIcon(':/movie-player/rock.png'))
        self.rlb.setCheckable(True)
        self.rlb.clicked.connect(lambda _: setattr(self.player, 'rock', self.rlb.isChecked()))
        self.addWidget(self.rlb)
        self.rlb.setToolTip("Rock")

        #home button
        self.hb = Button(icon=QIcon(':/movie-player/home.png'))
        self.hb.clicked.connect(lambda _: self.movieEvent("setViewBox"))
        self.addWidget(self.hb)
        self.hb.setToolTip("Home")

        #crop button
        self.cb = Button(icon=QIcon(':/movie-player/crop.png'))
        self.cb.setCheckable(True)
        self.cb.clicked.connect(lambda _: self.movieParam("crop", self.cb.isChecked()))
        self.addWidget(self.cb)
        self.cb.setToolTip("Zoom")
        self.changezoom.connect(lambda: self.cb.setChecked(False))

        #track button
        self.tb = Button(icon=QIcon(':/movie-player/track.png'))
        self.tb.setCheckable(True)
        self.tb.clicked.connect(lambda _: self.movieParam("track", self.tb.isChecked()))
        self.addWidget(self.tb)
        self.tb.setToolTip("Track zoomed location through movie")
        self.tb.setChecked(True)

        #speed slider
        self.ss = Slider(Qt.Horizontal)
        self.ss.setMinimum(1)
        self.ss.setMaximum(40)
        self.ss.setValue(int(1/self.player.speed))
        self.ss.sliderMoved.connect(lambda val: setattr(self.player, 'speed', 1/val))
        self.ss.sliderMoved.connect(lambda val: self.si.setText("%2dfps" % (val)))
        self.ss.setMinimumWidth(30)
        self.addWidget(self.ss)
        self.ss.setToolTip("Set Speed")

        #speed indicator
        self.si = QLabel()
        self.si.setStyleSheet("QLabel { color: #FFFFFF }")
        self.si.setText("10fps")
        self.addWidget(self.si)
        self.si.setToolTip("Speed")
        self.si.setMinimumWidth(50)
        self.si.setAlignment(Qt.AlignRight)

        #clipping range slider
        self.cs = Slider(Qt.Horizontal)
        self.cs.setMinimum(100)
        self.cs.setMaximum(1200)
        self.cs.setValue(self.movie[0][0].clim)
        self.cs.sliderMoved.connect(self.adjustClim)
        self.cs.sliderMoved.connect(lambda val: self.ci.setText("%04dG" % (val)))
        self.cs.setMinimumWidth(30)
        self.addWidget(self.cs)
        self.cs.setToolTip("Adjust Clipping Range")

        #clipping indicator
        self.ci = QLabel()
        self.ci.setStyleSheet("QLabel { color: #FFFFFF }")
        self.ci.setText("%4dG" % (self.movie[0][0].clim))
        self.addWidget(self.ci)
        self.setToolTip("Clipping Range")
        self.ci.setMinimumWidth(50)
        self.ci.setAlignment(Qt.AlignRight)

        #pointer indicator
        self.pi = QLabel()
        self.addWidget(self.pi)
        self.pi.setToolTip("Pointer Location")
        self.pi.setMinimumWidth(50)
        self.pi.setStyleSheet("QLabel { color: #FFFFFF }")
        self.pointerupdate.connect(lambda val: self.pi.setText(val[0]))
        self.pi.setAlignment(Qt.AlignRight)

        self.pi2 = QLabel()
        self.addWidget(self.pi2)
        self.pi2.setToolTip("Pointer Location")
        self.pi2.setMinimumWidth(50)
        self.pi2.setStyleSheet("QLabel { color: #FFFFFF }")
        self.pointerupdate.connect(lambda val: self.pi2.setText(val[1]))
        self.pi2.setAlignment(Qt.AlignRight)

        self.pi3 = QLabel()
        self.addWidget(self.pi3)
        self.pi3.setToolTip("Pointer Value")
        self.pi3.setMinimumWidth(75)
        self.pi3.setStyleSheet("QLabel { color: #FFFFFF }")
        self.pointerupdate.connect(lambda val: self.pi3.setText(val[2]))
        self.pi3.setAlignment(Qt.AlignRight)

        #main slider
        self.ms = Slider(Qt.Horizontal)
        self.ms.setMinimum(0)
        self.ms.setMaximum(self.size - 1)
        self.ms.setValue(0)
        self.ms.setTickPosition(0)
        self.controllayout.addWidget(self.ms, 2, 0, 1, self.widgets)
        self.ms.sliderMoved.connect(lambda _: self.pb.toggle(None, state=True))
        self.ms.sliderMoved.connect(self.player.set)
        self.player.updateSlider.connect(lambda x: self.ms.setValue(x))
        self.ms.setMaximumWidth(16777215)

        #trimming slider
        self.ts = RangeSlider(self.player.bp, Qt.Horizontal)
        self.ts.sliderMoved.connect(self.updateRange)
        self.controllayout.addWidget(self.ts, 3, 0, 1, self.widgets)
        self.ts.setToolTip("Adjust Playback Range")

        # image label
        self.pl = QLabel()
        self.pl.setStyleSheet("QLabel { color: #FFFFFF }")
        self.pl.setText(f"01/{self.size}")
        self.controllayout.addWidget(self.pl, 2, self.widgets)
        self.player.updateIdx.connect(lambda i: self.pl.setText("%02d/%02d" % (self.player.i + 1, self.size)))
        self.pl.setMinimumWidth(50)
        self.pl.setAlignment(Qt.AlignRight)

    def addWidget(self, w):
        self.controllayout.addWidget(w, 1, self.widgets)
        self.widgets += 1

    def step(self, i:int):
        self.pb.toggle(None, state=True)
        self.player.set(i)
        self.ms.setValue(i)

    def adjustClim(self, val:int):
        for movie in util.flatten(self.movie):
            movie.clim = val
            movie.updateImage(self.player.i)

    def updateRange(self, val:tuple):
        (u, l) = val 
        self.player.fp = int(u) 
        self.player.bp = int(l + 1) 

    def movieEvent(self, event:str, *args, **kwargs):
        for movie in util.flatten(self.movie):
            getattr(movie, event)(*args, **kwargs)
    
    def movieParam(self, param:str, val):
        for movie in util.flatten(self.movie):
            setattr(movie, param, val)