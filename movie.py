from PyQt5.QtCore import pyqtSignal, QThread, Qt, QRectF, QPointF
from PyQt5.QtGui import QTransform, QPen, QFont
from PyQt5.QtWidgets import *

from astropy.coordinates import SkyCoord
import astropy.units as u

import pyqtgraph as pg
from widgets import *
import numpy as np
import time, util, resources, math, projections, sunpy

class Movie(pg.GraphicsView):

    #required parameters
    player = None #Player object that tells this object which frame to show
    maps = [] #mlist object which contains the maps to be played
    moviePlayerQTParent = None #parent that contains this widget
    type = None #any child class of Projection_, specifying the map projection that this movie player will play
    
    #properties - most are automatically managed by this widget
    imgs = [] #raw np arrays of image data; the movie player will handle the transforming and cutting the data as needed
    frames = [] #represents the location of each frame within the original image
    clim = 1000 #clipping value for color scales
    scale = None #image scale (determined by height)
    
    #button states
    crop = False
    track = True

    #temporary
    rect = None #used to keep track of crop rectangle
    rectStart = [None, None] #original click location of crop rectangle
    pos = None #pointer location
    last_i = 0
    ticks = None
    lines = [[]]

    def __init__(self, **kwargs): 
        super().__init__(useOpenGL=True)

        for key, value in kwargs.items(): #take all params in kwargs and set them as attributes
            setattr(self, key, value)
        self.scale = list(self.type.get_scales())[-1]
        self.player.updateIdx.connect(self.updateImage) #connect player to self - when player emits the signal, the command to switch frames will run

        self.imgs = self.maps.getData(self.type, self.scale) #get transformed images for movie player (HMI returns flipped images) with right resolution

        self.ci = pg.GraphicsLayout()
        self.setCentralItem(self.ci)

        self.plot = self.ci.addPlot(title="") #create main plot for movie
        self.plot.setDefaultPadding(padding=0) #remove padding around plot
        self.plot.setMouseEnabled(x=False, y=False) #disable scrolling/panning for now TODO: enable scrolling/panning but set limits (don't want user to scroll/pan off screen)
        self.plot.setMenuEnabled(enableMenu=False) #disable pyqtgraph right click menu - using it messes up a lot of stuff here
        self.plot.scene().sigMouseClicked.connect(self.mouseClick) #connect mouse signals to respective handler functions
        self.plot.scene().sigMouseMoved.connect(self.mouseMove)

        self.img = pg.ImageItem() #image item to plot our images
        self.plot.setAspectLocked() #disable stretch to fill
        self.setViewBox() #generate viewboxes for each frame

        #TODO: add support for ticks and lat/lon lines
        self.plot.getAxis('left').setLabel(text=f"{self.type.cname} Latitude", units=self.type.unit)
        self.plot.getAxis('left').enableAutoSIPrefix(enable=False)
        self.plot.getAxis('bottom').setLabel(text=f"{self.type.cname} Longitude", units=self.type.unit)
        self.plot.getAxis('bottom').enableAutoSIPrefix(enable=False)
        self.plot.addItem(self.img)

    def updateImage(self, i): #called by Player object
        self.img.setImage(self.imgs[i]) #change actual image data
        self.img.setLevels([-self.clim, self.clim]) #set contrast for new image
        self.mouseMove(self.pos) #update pointer location
        self.plot.getAxis('left').setTicks([self.ticks[i][1]])
        self.plot.getAxis('bottom').setTicks([self.ticks[i][0]])

        #UNCOMMENT FOR LON/LAT LINES
        # for item in self.lines[self.last_i]:
        #     for line in item:
        #         self.plot.removeItem(line)
        # for item in self.lines[i]:
        #     for line in item:
        #         self.plot.addItem(line)
        # self.last_i = i

    def mouseClick(self, event):
        if self.rect is None and self.crop: #start crop border
            self.rect = QGraphicsRectItem(event.scenePos().x(), event.scenePos().y(), 0, 0)
            pen = QPen(Qt.white)
            self.rect.setPen(pen)
            self.plot.scene().addItem(self.rect)
            self.rectStart = event.scenePos()
            self.moviePlayerQTParent.pb.toggle(None, state=True)

        elif self.rect is not None: #stop crop border
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
        
        #update zoom rectangle if currently in zoom mode
        if self.rect is not None and pos is not None:
            self.rect.setRect(QRectF(min(self.rectStart.x(), pos.x()), min(self.rectStart.y(), pos.y()), abs(self.rectStart.x() - pos.x()), abs(self.rectStart.y() - pos.y())))
        elif self.rect is not None and not self.crop:
            self.plot.scene().removeItem(self.rect)
            self.rect = None

        #update mouse position and value measurements
        self.pos = pos
        pos = self.plot.getViewBox().mapSceneToView(pos)
        try: 
            x, y = (int(pos.x() + 0.5), int(pos.y() + 0.5))
            # print(x, y)
            value = self.imgs[self.player.i][x][y]
            if value is not None and not math.isnan(value):
                v = "%07.3fG" % (float(value/((4096/self.scale)**2)))
            else:
                v = " ---.---G"
        except IndexError:
            v = " ---.---G"
        
        #since current coordinates are probably from a scaled down or cropped version, the pixel coordinates might be different from those of the original map
        try:
            xp, yp = self.type.inverse_transform((pos.x(), pos.y()), self.scale) #wcs.pixel_to_world seems to be swapping lat and lon from the input
            x, y = self.type.get_lat_lon(self.maps[str(self.type) + str(self.scale)][self.player.i].wcs.pixel_to_world(yp, xp))
            self.moviePlayerQTParent.pointerupdate.emit(['''%04d"''' % (x), '''%04d"''' % (y), v])
        except ValueError:
            x = "---"
            y = "---"
            self.moviePlayerQTParent.pointerupdate.emit(["---", "---", v])

        #print(pos.x(), pos.y())

    def setViewBox(self, frame=None): 
        h = list(self.type.get_scales())[-1]
        w = h * self.type.ratio
        #IMPORTANT: self.frames must be scaled to within original resolution for crop to work
        if frame is None:
            self.frames = [QRectF(0, 0, w, h)] * len(self.imgs)
        elif not self.track:
            #gets coordinates of input frame
            tl = frame.topLeft()
            br = frame.bottomRight()
            #gets coordinate range of input frame
            w1, h1 = self.imgs[self.player.i].shape
            #gets output range for self.frames
            tl1 = self.frames[self.player.i].topLeft()
            br1 = self.frames[self.player.i].bottomRight()
            #calculates frame location within original image (before downscaling and cropping)
            x2 = util.scale(br.x(), (0, w1), (tl1.x(), br1.x()))
            y2 = util.scale(br.y(), (0, h1), (tl1.y(), br1.y()))
            x1 = util.scale(tl.x(), (0, w1), (tl1.x(), br1.x()))
            y1 = util.scale(tl.y(), (0, h1), (tl1.y(), br1.y()))
            self.frames = [QRectF(x1, y1, x2 - x1, y2 - y1)] * len(self.imgs)
        else: 
            #gets coordinates of input frame
            tl = frame.topLeft()
            br = frame.bottomRight()
            #gets coordinate range of input frame
            w1, h1 = self.imgs[self.player.i].shape
            #gets output range for self.frames
            tl1 = self.frames[self.player.i].topLeft()
            br1 = self.frames[self.player.i].bottomRight()
            #calculates frame location within original image (before downscaling and cropping)
            x2 = util.scale(br.x(), (0, w1), (tl1.x(), br1.x()))
            y2 = util.scale(br.y(), (0, h1), (tl1.y(), br1.y()))
            x1 = util.scale(tl.x(), (0, w1), (tl1.x(), br1.x()))
            y1 = util.scale(tl.y(), (0, h1), (tl1.y(), br1.y()))
            #parameters for rotation
            x = (x1 + x2)/2
            y = (y1 + y2)/2
            w = x2 - x1
            h = y2 - y1
            xp, yp = self.type.inverse_transform((x, y), list(self.type.get_scales())[-1]) #x, y, w, h assume max scaling
            # print(xp, yp)
            #creates SkyCoord from original image
            center = self.maps[str(self.type) + str(list(self.type.get_scales())[-1])][self.player.i].wcs.pixel_to_world(yp, xp)
            self.frames = []
            # print(center)
            for i in range(len(self.maps)):
                m = self.maps[str(self.type) + str(list(self.type.get_scales())[-1])][i]
                # print(type(m.coordinate_frame))
                c = util.rotate(center, (m.date - self.maps[str(self.type) + str(self.scale)][self.player.i].date).to(u.day), out_frame=m.coordinate_frame)
                # print(c)
                b, a = self.type.transform_coord(m.wcs.world_to_pixel(c), list(self.type.get_scales())[-1])
                self.frames.append(QRectF(a - w/2, b - h/2, w, h))
                # print(self.frames[-1])

        # print(self.views[0].topLeft().x(), self.views[0].topLeft().y(), self.views[0].bottomRight().x(), self.views[0].bottomRight().y())
        self.imgs, self.scale = self.maps.crop(self.frames, self.type)
        self.calc_ticks()
        self.updateImage(self.player.i)

    def calc_ticks(self, lines=False, res=1): 
        #res indicates the number of extra points calculated to generate lines - higher means slower but more curved if lines are straight, then use res=1
        #lines must be true for graphs with curved lon/lat lines, otherwise ticks will be inaccurate
        #WARNING, setting lines=True is REALLY messed up it's slow and messy, but it works. Remember to uncomment corresponding part in update_image

        #I dont have the time to add comments, but if you want to see how it works, check test2.py
        
        lines = []
        ticks = []
        for n in range(len(self.frames)):
            m = self.maps[str(self.type) + str(list(self.type.get_scales())[-1])][n]
            wp, hp = self.type.transform(m.data).shape
            m2 = self.maps[str(self.type) + str(self.scale)][n]
            # print(self.frames[i].topRight().x())

            bl = m.wcs.pixel_to_world(self.frames[n].bottomLeft().x(), self.frames[n].topRight().y()).transform_to(sunpy.coordinates.HeliographicStonyhurst)
            tr = m.wcs.pixel_to_world(int(self.frames[n].topRight().x() - 0.99), int(self.frames[n].bottomLeft().y() - 0.99)).transform_to(sunpy.coordinates.HeliographicStonyhurst)
            # print(bl, tr)

            hd = tr.lat.degree - bl.lat.degree
            wd = tr.lon.degree - bl.lon.degree

            if hd <= 15:
                hi = 1
            elif hd/5 <= 6:
                hi = 5
            elif hd/10 <= 9:
                hi = 10
            else:
                hi = 30
            if wd <= 15:
                wi = 1
            elif wd/5 <= 6:
                wi = 5
            elif wd/10 <= 9:
                wi = 10
            else:
                wi = 30

            yticks = []
            for i in range(-2, int(hd/hi + 0.5) + 2):
                yticks.append(bl.lat.degree - bl.lat.degree%hi + hi*(i + 1))
            xticks = []
            for i in range(-2, int(wd/wi + 0.5) + 2):
                xticks.append(bl.lon.degree - bl.lon.degree%wi + wi*(i + 1))

            # print(xticks, yticks)
            if not lines:
                xtickpixels = []
                ytickpixels = []
                for t in xticks:
                    xmin, xmax = self.type.xrange
                    if t < xmin or t > xmax:
                        continue
                    yp, xp = self.type.transform_coord(m2.wcs.world_to_pixel(SkyCoord(t*self.type.u, 0*self.type.u, frame=m2.coordinate_frame)))
                    xtickpixels.append((xp - self.frames[n].topLeft().x() * self.scale/list(self.type.get_scales())[-1], str(int(t))))
                for t in yticks:
                    ymin, ymax = self.type.yrange
                    if t < ymin or t > ymax:
                        continue
                    yp, xp = self.type.transform_coord(m2.wcs.world_to_pixel(SkyCoord(0*self.type.u, t*self.type.u, frame=m2.coordinate_frame)))
                    ytickpixels.append((yp - self.frames[n].topLeft().y() * self.scale/list(self.type.get_scales())[-1], str(int(t))))
                ticks.append([xtickpixels, ytickpixels])
                continue

            xpts = []
            for i in range(len(xticks) - 1):
                xpts.extend(np.linspace(xticks[i], xticks[i + 1], num=res).tolist())
            xpts.append(xticks[-1])

            ypts = []
            for i in range(len(yticks) - 1):
                ypts.extend(np.linspace(yticks[i], yticks[i + 1], num=res).tolist())
            ypts.append(yticks[-1])

            # print(xpts, ypts)

            xtickpixels = []
            xlines = []
            for i, x in enumerate(xticks):
                pos = False
                low = True
                pts = []
                for j, y in enumerate(ypts):
                    xmin, xmax = self.type.xrange
                    ymin, ymax = self.type.yrange
                    if x < xmin or x > xmax or y < ymin or y > ymax:
                        continue
                    yp, xp = self.type.transform_coord(m2.wcs.world_to_pixel(SkyCoord(x*self.type.u, y*self.type.u, frame=m2.coordinate_frame)))
                    if xp >= 0 and xp < wp and yp >= 0 and yp < hp:
                        pos = True
                    if low and yp > 0:
                        if len(pts) > 0: 
                            pts = [pts[-1]]
                            xtickpixels.append((xp - yp*(xp - pts[0][0])/(yp - pts[0][1]) - self.frames[n].topLeft().x() * self.scale/list(self.type.get_scales())[-1], str(int(x))))
                        else:
                            xtickpixels.append((xp - self.frames[n].topLeft().x() * self.scale/list(self.type.get_scales())[-1], str(int(x))))
                        low = False
                    pts.append([xp - self.frames[n].topLeft().x(), yp - self.frames[n].topLeft().y()])
                    if yp > hp:
                        # print("exited on", j)
                        break
                if not pos: continue
                line = pg.PlotDataItem(np.array(pts), antialias=True)
                xlines.append(line)
            ytickpixels = []
            ylines = []
            for j, y in enumerate(yticks):
                pos = False
                low = True
                pts = []
                for i, x in enumerate(xpts):
                    xmin, xmax = self.type.xrange
                    ymin, ymax = self.type.yrange
                    if x < xmin or x > xmax or y < ymin or y > ymax:
                        continue
                    yp, xp = self.type.transform_coord(m2.wcs.world_to_pixel(SkyCoord(x*self.type.u, y*self.type.u, frame=m2.coordinate_frame)))
                    if xp >= 0 and xp < wp and yp >= 0 and yp < hp:
                        pos = True
                    if low and xp > 0:
                        if len(pts) > 0: 
                            pts = [pts[-1]]
                            ytickpixels.append((yp - xp*(yp - pts[0][1])/(xp - pts[0][0]) - self.frames[n].topLeft().y() * self.scale/list(self.type.get_scales())[-1], str(int(y))))
                        else:
                            ytickpixels.append((yp - self.frames[n].topLeft().y() * self.scale/list(self.type.get_scales())[-1], str(int(y))))
                        low = False
                    pts.append([xp - self.frames[n].topLeft().x(), yp - self.frames[n].topLeft().y()])
                    if xp > wp:
                        break
                if not pos: continue
                line = pg.PlotDataItem(np.array(pts), antialias=True)
                ylines.append(line)
            lines.append([xlines, ylines])
            ticks.append([xtickpixels, ytickpixels])
        self.lines = lines
        self.ticks = ticks
        print(self.ticks)





class Player(QThread): #used to control all frame changes in Movie class(es) - all instances of Movie should be connected to one player

    updateIdx = pyqtSignal(int) #emitted whenever player.i is changed
    updateSlider = pyqtSignal(int) #emitted whenever the player increments i - used to update slider in MoviePlayerQt Class
    reverseSignal = pyqtSignal(bool) #used when bounce is enabled - emitted whenever the player 'bounces' and therefore needs to update the reverse button state

    speed = 0.1 #time interval between frames

    i = 0 #current state of movie - all Movie classes and slider should be bound to this variable in some way
    fp = 0 #front pointer - minimum value for i depending on rangeslider
    bp = 0 #back pointer - maximum value for i depending on rangeslider

    paused = True
    reverse = False
    rock = False

    def __init__(self, size):
        self.bp = size
        super().__init__()

    def run(self): #constantly increments i with time interval [speed] whenever [paused] is false
        while True:
            while self.paused:
                time.sleep(0.1)
            self.inc()
            time.sleep(self.speed)

    def inc(self): #function for incrementing i = checks to make sure i does not exceed fp and bp and adjusts according to reverse/rock state
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

    def set(self, i): #used to manually set [i] - this is usually connected to the progress slider in MoviePlayerQt
        self.i = i
        self.updateIdx.emit(i)

class MList(dict): #handles all data processing related tasks - note that this is a modified dictionary and can therefore be accessed like a dict
    def __init__(self, maps): #maps are assumed to be in hpc coordinates - all maps are automatically downscaled on init
        super().__init__()
        self['hpc4096'] = maps
        self['hpc2048'] = [m.superpixel([2, 2]*u.pix) for m in self['hpc4096']]
        self['hpc1024'] = [m.superpixel([2, 2]*u.pix) for m in self['hpc2048']]

    def __len__(self): #length should be number of frames total instead of number of keys in the dictionary
        return len(self['hpc4096'])
        
    def getData(self, type, scale): #returns a list of data transformed for use by Movie class (raw data is sometimes rotated or upside down)
        return [type.transform(m.data) for m in self[str(type) + str(scale)]]

    def transform(self, projection, **kwargs): #projects to new map projection (should be Projection class - see projections.py) **kwargs is transferred to the projections from_hpc method
        scales = list(projection.get_scales())
        scales.reverse()
        self[str(projection) + str(scales[0])] = [projection.from_hpc(m, h=scales[0], **kwargs) for m in self['hpc4096']]
        for i, scale in enumerate(scales[1:]):
            ratio = int(scales[i]/scale + 0.1) #i is shifted down because we are iterating through cut down list
            self[str(projection) + str(scale)] = [m.superpixel([ratio, ratio]*u.pix) for m in self[str(projection) + str(scales[i])]] 

    def crop(self, views, type): #returns a list of cropped images given by frames in the list [views] - automatically upscales depending on zoom and automatically fills null space with zeros
        h = list(type.get_scales())[-1]
        w = h * type.ratio
        ans = []
        for i, view in enumerate(views):
            topLeft = view.topLeft()
            bottomRight = view.bottomRight()
            sl = max((bottomRight.x() - topLeft.x())/type.ratio, topLeft.y(), - bottomRight.y())
            # print(sl)
            scale = type.get_scale(sl)
            # print(scale)
            # print(w, h)
            # print(topLeft.x(), topLeft.y(), bottomRight.x(), bottomRight.y())
            x1 = int(util.scale(topLeft.x(), (0, w), (0, scale*type.ratio)) + 0.5)
            y1 = int(util.scale(topLeft.y(), (0, h), (0, scale)) + 0.5)
            x2 = int(util.scale(bottomRight.x(), (0, w), (0, scale*type.ratio)) + 0.5)
            y2 = int(util.scale(bottomRight.y(), (0, h), (0, scale)) + 0.5)
            #no need to transform coords here because we are slicing on transformed array
            # print(x1, y1, x2, y2)
            # print(type.transform(self[str(type) + str(scale)][i].data).shape)

            ans.append(util.slice_extend(type.transform(self[str(type) + str(scale)][i].data), x1, x2, y1, y2))
        return ans, scale

class MoviePlayerQT(QWidget): #main movie class - this is the only object that should be used outside of movie.py

    size = 0 #length of movie in frames
    widgets = 0 #internal widgets counter for loading

    changezoom = pyqtSignal() #called by movie class whenever zoom is changed - this is used to uncheck the zoom button when zoom is completed
    pointerupdate = pyqtSignal(list) #called by movie class whenever pointer is updated - used to update pointer info labels

    def __init__(self, maps, **kwargs): #loads widgets and initializes movie players
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

        self.movie = [[Movie(maps=self.maps, player=self.player, moviePlayerQTParent=self, type=projections.CylindricalEqualArea)]]
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

    def addWidget(self, w): #helper function to append a widget to the controls bar (so I don't have to keep track of indexing)
        self.controllayout.addWidget(w, 1, self.widgets)
        self.widgets += 1

    def step(self, i:int): #function called by step button
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

    def movieEvent(self, event:str, *args, **kwargs): #used to call [event] function in all instances in self.Movie *args any additional parameters are inputted when calling [event]
        for movie in util.flatten(self.movie):
            getattr(movie, event)(*args, **kwargs)
    
    def movieParam(self, param:str, val): #used to change [param] attrivute in all instances of Movie in self.Movie
        for movie in util.flatten(self.movie):
            setattr(movie, param, val)