from PyQt5.QtCore import QThread, pyqtSignal, Qt, QSize, QTimer
from PyQt5.QtWidgets import *
from PyQt5.QtGui import QIcon

import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.patches import Rectangle

from superqt import QRangeSlider
import astropy.units as u
import time, util, resources


class Movie(FigureCanvasQTAgg):

    r = 0 #row/column of movie player inside widget
    c = 0
    mode = None
    images = []
    im = []
    running = False
    i = 0
    min = 0
    max = None
    real = True #whether or not the current image is 'real' or a blitted background
    figs = []
    scale = 1024
    time = None
    coordinates = "-"
    value = "-"
    xp = 0
    yp = 0
    zoom = [False, [-1, -1]] # [state (False, True), [start x, start y]
    changeZoom = pyqtSignal(dict)
    pointerUpdate = pyqtSignal(str)
    crop = False
    crop_frame = None
    crop_time = None
    rotate = True
    type = 'helioprojective'
    skip_redraw = False

    def __init__(self, maps, player, clim=1000, w=640, h=480, cea=False, parent=None, **kwargs):
        self.clim = clim
        self.w = w
        self.h = h
        self.cea = cea
        self.maps = maps

        for map in self.maps:
            map.pre_scale(self.scale)

        px = 1 / plt.rcParams['figure.dpi']
        plt.ioff()

        self.fig_width = self.w * px
        self.fig_height = self.h * px

        for key, value in kwargs.items():
            setattr(self, key, value)

        fig, _, im = self.maps[0].plot(clim=self.clim, cea=self.cea, scale=self.scale, crop=self.crop, frame=self.crop_frame, rot=self.rotate, start_time=self.crop_time, skip_reset=True)
        fig.canvas.draw()
        self.figure = fig

        FigureCanvasQTAgg.__init__(self, self.figure)
        self.draw()
        fig.set_size_inches(self.fig_width, self.fig_height)

        self.setParent(parent)
        self.player = player
        self.player.update_idx.connect(self.update_image)

    def connect_events(self):
        self.mpl_connect('button_press_event', self.click)
        self.mpl_connect('button_press_event', self.zoom_handler)
        self.mpl_connect('button_release_event', self.zoom_handler)
        self.mpl_connect('motion_notify_event', self.zoom_handler)
        self.mpl_connect('motion_notify_event', self.mouse_move)

    def update_image(self):
        if self.real:
            self.redraw()
        self.restore_region(self.images[self.player.i])
        self.blit(self.figs[self.player.i].bbox)
        self.update_process(self.player.i)
        self.real = False
        self.time = str(self.maps[self.player.i].date)
        if self.xp is not None and self.yp is not None:
            self.value = self.maps[self.player.i].var[self.type].data[int(self.xp + 0.5)][int(self.yp + 0.5)]
        self.update_pointer()

    def click(self, event):
        print(event.xdata, event.ydata)

    def zoom_handler(self, event):
        if event.name == "button_press_event":
            self.press_zoom(event)
        if event.name == "motion_notify_event":
            self.drag_zoom(event)
        if event.name == "button_release_event":
            self.release_zoom(event)

    def update_process(self, i):
        return

    def update_pointer(self):
        if self.value is not None and self.value != '-':
            value = "%07.3fG" % (abs(float(self.value)))
            if float(self.value) >= 0:
                value = " " + value
            else:
                value = "-" + value
        else:
            value = " ---.---G"

        try:
            temp = self.coordinates.strip('(world)').strip(' ').replace('"', "").split()
            coordinates = '''%04d" %04d"''' % (int(temp[0]), int(temp[1]))
        except ValueError:
            coordinates = '----" ----"'

        self.pointerUpdate.emit(f"{self.time} {coordinates} {value}")

    def redraw(self):
        self.fig_width, self.fig_height = self.figure.get_size_inches()
        # print("drawing")
        self.images = []
        self.figs = []
        self.im = []
        # pre-draws every frame
        for i in range(len(self.maps)):
            fig, _, im = self.maps[i].plot(clim=self.clim, cea=self.cea, scale=self.scale, crop=self.crop, frame=self.crop_frame, rot=self.rotate, start_time=self.crop_time)
            fig.set_size_inches(self.fig_width, self.fig_height)
            self.figs.append(fig)
            fig.canvas.draw()
            self.im.append(im)

            image = fig.canvas.copy_from_bbox(fig.bbox)
            self.images.append(image)
        # print("done drawing")

        self.figure = self.figs[self.player.i]

        self.connect_events()
        self.draw_idle()

    def draw_specific(self, i):
        fig, _, im = self.maps[i].plot(clim=self.clim, cea=self.cea, scale=self.scale, crop=self.crop, frame=self.crop_frame)
        fig.set_size_inches(self.fig_width, self.fig_height)
        self.figs[i] = fig
        fig.canvas.draw()
        self.im[i] = im

        image = fig.canvas.copy_from_bbox(fig.bbox)
        self.images[i] = image

    def adjust_clim(self, clim): #used to momentarily adjust clim of current frame
        if not self.real:
            self.figure = self.figs[self.player.i]
            self.real = True
            self.connect_events()
        self.im[self.player.i].set_clim(-clim, clim)
        self.clim = clim
        self.draw_idle()

    def mouse_move(self, event):
        if event.xdata is None:
            self.coordinates = "-"
            self.value = "-"
            self.xp = None
            self.yp = None
        else:
            try:
                self.coordinates = str(self.figure.axes[0].format_coord(event.xdata, event.ydata))
                self.value = self.maps[self.player.i].var[self.type].data[int(event.ydata + 0.5)][int(event.xdata + 0.5)]
            except:
                self.coordinates = "-"
                self.value = "-"
            self.xp = event.xdata
            self.yp = event.ydata
        self.update_pointer()

    def press_zoom(self, event):
        if self.mode != 'zoom' or event.x is None or event.y is None or not self.figure.get_axes()[0].in_axes(event):
            return

        self.paused = True

        if self.real:
            self.draw_specific(self.player.i)
            self.real = False
            self.update_image()

        self.zoom[0] = True
        self.zoom[1][0] = event.xdata
        self.zoom[1][1] = event.ydata
        self.zoomrect = Rectangle((event.xdata, event.ydata), 0, 0)
        self.figure.get_axes()[0].add_patch(self.zoomrect)

    def drag_zoom(self, event):
        if not self.zoom[0]:
            return
        self.restore_region(self.images[self.player.i])

        try:
            self.zoomrect.set_width(event.xdata - self.zoom[1][0])
        except TypeError:
            pass
        try:
            self.zoomrect.set_height(event.ydata - self.zoom[1][1])
        except TypeError:
            pass
        self.figure.get_axes()[0].draw_artist(self.zoomrect)
        FigureCanvasQTAgg.blit(self)
        self.flush_events()

    def release_zoom(self, event):
        if not self.zoom[0]:
            return
        self.zoomrect.remove()
        self.restore_region(self.images[self.player.i])
        self.blit()
        self.flush_events()
        self.zoom[0] = False
        self.mode = None

        # self.crop = True

        wcs = self.maps[self.player.i].var[self.type]
        top_right = wcs.pixel_to_world(max(self.zoom[1][0], event.xdata)*u.pix, max(self.zoom[1][1], event.ydata)*u.pix)
        bottom_left = wcs.pixel_to_world(min(self.zoom[1][0], event.xdata)*u.pix, min(self.zoom[1][1], event.ydata)*u.pix)

        self.crop_frame = (top_right, bottom_left)
        self.crop_time = self.maps[self.player.i].date

        if self.type[-6:0] == 'zoomed':
            self.crop=True
            fig, _, im = self.maps[self.player.i].plot(clim=self.clim, cea=self.cea, scale=self.scale, crop=self.crop, frame=self.crop_frame)
            fig.set_size_inches(self.fig_width, self.fig_height)
            self.figure = fig
            self.real = True
            self.connect_events()
            self.draw_idle()
            self.im[self.player.i] = im

        else:
            self.real = True
            self.figure = self.figs[self.i]
            self.changeZoom.emit({"r": self.r, "c": self.c, "crop_frame": self.crop_frame, "crop_time": self.crop_time, "type": self.type + ' zoomed', "crop": True, "rotate": self.rotate})

    def home(self):
        if not self.crop:
            return
        self.paused = True

        self.crop = False
        temp = self.maps[self.player.i].var[self.type]
        fig, _, im = self.maps[self.player.i].plot(clim=self.clim, cea=self.cea, scale=self.scale, crop=self.crop,
                                            frame=self.crop_frame)
        fig.set_size_inches(self.fig_width, self.fig_height)
        self.figure = fig
        self.real = True
        self.connect_events()
        self.draw_idle()
        self.maps[
            self.player.i].var[self.type] = temp
        self.im[self.player.i] = im

    def set_zoom(self, val):
        if val:
            self.mode = 'zoom'
        else:
            self.mode = None

class Player(QThread):

    update_idx = pyqtSignal(int)
    reverseSignal = pyqtSignal(bool)

    basespeed = 0.2
    speed = basespeed
    i = 0
    reverse = False
    rock = False
    min = 0
    max = None
    paused = True

    def __init__(self, min, max):
        self.min = min
        self.max = max
        super().__init__()

    def run(self):
        while True:
            self.inc_i()
            self.update_idx.emit(self.i)
            while self.paused:
                time.sleep(0.1)
            time.sleep(self.speed)

    def inc_i(self):
        if self.reverse: self.i -= 1
        else: self.i += 1
        if self.rock and self.i >= self.max:
            self.i -= 2
            self.toggle_reverse()
        elif self.rock and self.i < self.min:
            self.i += 2
            self.toggle_reverse()
        else: self.i = self.min + (self.i - self.min) % (self.max - self.min)

    def change_i(self, i):
        self.i = i
        self.update_idx.emit(i)

    def toggle_reverse(self, val=None):
        if val is not None:
            self.reverse = val
        else:
            self.reverse = not self.reverse
            self.reverseSignal.emit(self.reverse)

class Slider(QSlider):
    s = """
    QSlider {
        height: 10px;
        margin: 5px
    }
    QSlider::groove:horizontal { 
        height: 10px; 
        margin-bottom: -10px; 
        background-color: rgb(200, 200, 200);
        border-radius: 5px; 
    }
    QSlider::handle:horizontal { 
        border: none; 
        height: 10px; 
        width: 10px; 
        margin: 0px; 
        border-radius: 5px; 
        background-color: rgb(160, 175, 255); 
    }
    QSlider::handle:horizontal:hover {
        background-color: rgb(140, 155, 235);
    }
    QSlider::groove:vertical { 
        height: 10px; 
        margin: 0px; 
        background-color: rgb(200, 200, 200);
        border-radius: 5px; 
    }
    QSlider::handle:vertical { 
        border: none; 
        height: 10px; 
        width: 10px; 
        margin: 0px; 
        border-radius: 5px; 
        background-color: rgb(160, 175, 255); 
    }
    QSlider::handle:vertical:hover {
        background-color: rgb(140, 155, 235);
    }
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setStyleSheet(self.s)

    def mousePressEvent(self, event):  # click to set value
        super().mousePressEvent(event)
        if event.button() == Qt.LeftButton:
            val = self.pixelPosToRangeValue(event.pos())
            self.setValue(val)
            self.sliderMoved.emit(val)

    def pixelPosToRangeValue(self, pos):
        opt = QStyleOptionSlider()
        self.initStyleOption(opt)
        gr = self.style().subControlRect(QStyle.CC_Slider, opt, QStyle.SC_SliderGroove, self)
        sr = self.style().subControlRect(QStyle.CC_Slider, opt, QStyle.SC_SliderHandle, self)

        if self.orientation() == Qt.Horizontal:
            sliderLength = sr.width()
            sliderMin = gr.x()
            sliderMax = gr.right() - sliderLength + 1
        else:
            sliderLength = sr.height()
            sliderMin = gr.y()
            sliderMax = gr.bottom() - sliderLength + 1
        pr = pos - sr.center() + sr.topLeft()
        p = pr.x() if self.orientation() == Qt.Horizontal else pr.y()
        return QStyle.sliderValueFromPosition(self.minimum(), self.maximum(), p - sliderMin, sliderMax - sliderMin,
                                              opt.upsideDown)

    def keyPressEvent(self, event):
        # arrow keys move slider the wrong ways; this should override it
        self.parent().keyPressEvent(event)

class Button(QPushButton):
    s = """
            QPushButton { 
                border: none; 
                height: 20px; 
                width: 20px; 
                margin: 0px; 
                border-radius: 2px; 
                background-color: rgb(160, 175, 255); 
            }
            QPushButton::hover {
                background-color: rgb(140, 155, 235);
            }
            QPushButton::checked {
                background-color: rgb(120, 135, 215);
            }
            """

    def __init__(self, icon=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.setStyleSheet(self.s)
        if icon is not None: self.setIcon(icon)
        self.setIconSize(QSize(18, 18))

class PlayButton(Button):
    def __init__(self, *args, **kwargs):
        self.pause = QIcon(':/movie-player/pause.png')
        self.play = QIcon(':/movie-player/play.png')

        super().__init__(self.play, *args, **kwargs)

    def state(self, paused):
        if paused:
            self.setIcon(self.play)
            self.setIconSize(QSize(18, 18))
        else:
            self.setIcon(self.pause)
            self.setIconSize(QSize(18, 18))

class RangeSlider(QRangeSlider):

    ss = """
        QSlider {
            height: 1px;
            margin: 5px;
        }
        QSlider::groove:horizontal { 
            height: 1px; 
            background-color: white;
            border-radius: 0px; 
            margin-left: -6px;
            margin-right: -6px;
        }
        QSlider::handle {
            margin-top: -6px;
            margin-bottom: -6px; 
            image: url(:/slider/handle.png);
            width: 20px;
        }
        """

    def __init__(self, max, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setStyleSheet(self.ss)
        self.setMinimum(0)
        self.setMaximum(max - 1)
        self.setValue((0, max - 1))

class MoviePlayerQT(QWidget):

    i = 0
    change_idx = pyqtSignal(int)

    def __init__(self, maps, **kwargs):
        super().__init__(**kwargs)

        self.len = len(maps)
        self.maps = maps

        self.mainwidget = QWidget()
        self.setChildrenFocusPolicy(self.mainwidget, Qt.NoFocus)
        self.mainlayout = QVBoxLayout(self)
        self.layout = QGridLayout(self.mainwidget)
        self.setStyleSheet("QObject { background: white; }")
        self.mainlayout.addWidget(self.mainwidget)

        self.player = Player(0, len(maps))
        self.change_idx.connect(self.player.change_i)
        self.start = self.player.start

        self.movie = [[Movie(maps, self.player)]]
        self.movie[0][0].changeZoom.connect(lambda d: self.add_movie(**d))
        self.moviewidget = QWidget()
        self.movielayout = QGridLayout(self.moviewidget)
        self.layout.addWidget(self.moviewidget, 0, 0, 1, -1)
        for i, row in enumerate(self.movie):
            for j, movie in enumerate(row):
                self.movielayout.addWidget(movie, i, j)

        self.load_widgets()

        self.start()

        QTimer.singleShot(1000, self.startup)

    def load_widgets(self):
        # play/pause button
        self.pb = PlayButton()
        self.pb.clicked.connect(self.toggle)
        self.add_widget(self.pb)
        self.pb.setToolTip("Play/Pause")

        # back button
        self.bb = Button(icon=QIcon(':/movie-player/back.png'))
        self.bb.clicked.connect(lambda _: self.step(
            (self.player.i - 1) % len(self.maps)))
        self.add_widget(self.bb)
        self.bb.setToolTip("Back")

        # forward button
        self.fb = Button(icon=QIcon(':/movie-player/forward.png'))
        self.fb.clicked.connect(lambda _: self.step(
            (self.player.i + 1) % len(
                self.maps)))  # step is scaled based on speed multiplier
        self.add_widget(self.fb)
        self.fb.setToolTip("Forward")

        # play in reverse button
        self.rb = Button(icon=QIcon(':/movie-player/reverse.png'))
        self.rb.setCheckable(True)
        self.rb.clicked.connect(lambda _: self.player.toggle_reverse(val=self.rb.isChecked()))
        self.player.reverseSignal.connect(lambda val: self.rb.setChecked(val))
        self.add_widget(self.rb)
        self.rb.setToolTip("Play in Reverse")

        # rock/loop button
        self.rlb = Button(icon=QIcon(':/movie-player/rock.png'))
        self.rlb.setCheckable(True)
        self.rlb.clicked.connect(self.set_rock)
        self.add_widget(self.rlb)
        self.rlb.setToolTip("Rock/Loop")

        # home button
        self.hb = Button(icon=QIcon(':/movie-player/home.png'))
        self.hb.clicked.connect(self.home)
        self.add_widget(self.hb)
        self.hb.setToolTip("Home")

        # crop button
        self.cb = Button(icon=QIcon(':/movie-player/crop.png'))
        self.cb.setCheckable(True)
        for movie in util.flatten(self.movie):
            self.cb.clicked.connect(movie.set_zoom)
        self.add_widget(self.cb)
        self.cb.setToolTip("Zoom in")
        for movie in util.flatten(self.movie):
            movie.changeZoom.connect(lambda _: self.cb.setChecked(False))

        # track button
        self.tb = Button(icon=QIcon(':/movie-player/track.png'))
        self.tb.setCheckable(True)
        self.tb.clicked.connect(self.set_track)
        self.add_widget(self.tb)
        self.tb.setToolTip("Track zoomed location through movie")
        self.tb.setChecked(True)

        # speed slider
        self.ss = Slider(Qt.Horizontal)
        self.ss.setMinimum(-400)
        self.ss.setMaximum(400)
        self.ss.setValue(0)
        self.ss.sliderMoved.connect(self.update_speed)
        self.ss.setMinimumWidth(50)
        self.add_widget(self.ss)
        self.ss.setToolTip("Set Speed")

        # speed indicator
        self.si = QLabel()
        self.si.setText("1.00x")
        self.add_widget(self.si)
        self.si.setToolTip("Speed")

        # clipping range slider
        self.cs = Slider(Qt.Horizontal)
        self.cs.setMinimum(100)
        self.cs.setMaximum(1200)
        self.cs.setValue(self.movie[0][0].clim)
        self.cs.sliderMoved.connect(self.adjust_clim)
        self.cs.sliderMoved.connect(lambda val: self.ci.setText("%4dG" % (val)))
        self.cs.setMinimumWidth(50)
        self.add_widget(self.cs)
        self.cs.setToolTip("Adjust Clipping Values")

        # clipping indicator
        self.ci = QLabel()
        self.ci.setText("1000G")
        self.add_widget(self.ci)
        self.cs.setToolTip("Clipping Values")

        # pointer indicator
        self.pi = QLabel()
        self.add_widget(self.pi)
        self.pi.setToolTip("Time Location Value")
        for movie in util.flatten(self.movie):
            movie.pointerUpdate.connect(lambda val: self.pi.setText(val))
        self.pi.setMinimumWidth(240)

        # progressbar
        self.sl = Slider(Qt.Horizontal)
        self.sl.setMinimum(0)
        self.sl.setMaximum(len(self.maps) - 1)
        self.sl.setValue(0)
        self.sl.setTickPosition(0)
        self.layout.addWidget(self.sl, 2, 0, 1, self.i)
        self.sl.sliderMoved.connect(self.slider)
        self.player.update_idx.connect(self.update_slider)
        self.sl.setMaximumWidth(16777215)

        # trimming slider
        self.ts = RangeSlider(self.player.max, Qt.Horizontal)
        self.ts.sliderMoved.connect(self.update_range)
        self.layout.addWidget(self.ts, 3, 0, 1, self.i)
        self.ts.setToolTip("Adjust Playback Range")

        # image label
        self.pl = QLabel()
        self.pl.setText(f'1/{len(self.maps)}')
        self.layout.addWidget(self.pl, 2, self.i)

    def startup(self):
        # everything breaks without these few lines even though it essentially does nothing; dont worry about it :)
        self.player.change_i(0)
        self.player.change_i(1)

        for movie in util.flatten(self.movie):
            movie.figure = movie.figs[self.player.i]
            movie.real = True
            movie.connect_events()
            movie.draw_idle()

        self.player.change_i(1)
        self.player.change_i(0)

    def setChildrenFocusPolicy(self, w, policy):
        def recursiveSetChildFocusPolicy(parentQWidget):
            for childQWidget in parentQWidget.findChildren(QWidget):
                childQWidget.setFocusPolicy(policy)
                recursiveSetChildFocusPolicy(childQWidget)

        recursiveSetChildFocusPolicy(w)

    def slider(self, val):
        self.toggle(True, state=True)
        self.change_idx.emit(val)
        self.pl.setText(f'{val + 1}/{self.len}')

    def update_slider(self, i):
        self.pl.setText(f'{i + 1}/{self.len}')
        self.sl.setValue(i)

    def toggle(self, _, state=None):  # first parameter so that we can connect toggle to "update_slider"
        if state is not None:
            self.player.paused = state
        else:
            self.player.paused = (not self.player.paused)

        self.pb.state(self.player.paused)

    def step(self, i):
        self.update_slider(i)
        self.sl.sliderMoved.emit(i)

    def update_speed(self, val):
        # scale so that 1/3x and 3x are the same distance from center
        if val <= 0:
            multiplier = -1 / (val / 100 - 1)
        else:
            multiplier = 1 + val / 100

        self.si.setText("%1.2fx" % (multiplier))
        self.player.speed = self.player.basespeed / multiplier

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Space:
            self.toggle(None)
        elif event.key() == Qt.Key_Left:
            self.step((self.player.i - max(1, int(self.player.basespeed / self.player.speed + 0.5))) % self.len)
        elif event.key() == Qt.Key_Right:
            self.step((self.player.i + max(1, int(self.player.basespeed / self.player.speed + 0.5))) % self.len)

    def update_range(self, val):
        (min, max) = val
        self.player.max = int(max + 1)
        self.player.min = int(min)

    def add_widget(self, w):
        self.layout.addWidget(w, 1, self.i)
        self.i += 1

    def set_rock(self, val):
        self.player.rock = val

    def adjust_clim(self, val):
        for movie in util.flatten(self.movie):
            movie.adjust_clim(val)
        self.toggle(True, True)

    def set_track(self, val):
        for movie in util.flatten(self.movie):
            movie.rotate = val
            movie.real = True
            movie.figure = movie.figs[movie.player.i]

    def add_movie(self, **kwargs):
        try:
            try:
                m = self.movie[kwargs["r"]][kwargs["c"] + 1]

                m.crop = True
                m.crop_frame = kwargs["crop_frame"]
                m.crop_time = kwargs["crop_time"]

                m.draw_specific(self.player.i)
                m.figure = m.figs[self.player.i]
            except IndexError:
                m = self.movie[kwargs["r"]][kwargs["c"]]
                for map in m.maps:
                    map.var[m.type + " zoomed"] = map.var[m.type]
                m = Movie(self.maps, self.player, **kwargs)
                self.movie[kwargs["r"]].append(m)
                self.movielayout.addWidget(self.movie[kwargs["r"]][-1], kwargs["r"], kwargs["c"] + 1)

                m.pointerUpdate.connect(lambda val: self.pi.setText(val))
                self.cb.clicked.connect(m.set_zoom)

        except ValueError:
            print("something went wrong, please try again")

    def home(self):
        for movie in util.flatten(self.movie):
            movie.home()