import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg

from PyQt5.QtCore import QThread, pyqtSignal, Qt, QSize, QTimer
from PyQt5.QtWidgets import *
from PyQt5.QtGui import QIcon
from superqt import QRangeSlider
from matplotlib.patches import Rectangle
import astropy.units as u
import time, _thread, math, resources


class Movie(FigureCanvasQTAgg):

    mode = None
    basespeed = 0.2
    speed = basespeed  # one frame every 0.5 seconds
    images = []
    im = []
    running = False
    paused = True
    i = 0
    min = 0
    max = None
    real = True #whether or not the current image is 'real' or a blitted background
    figs = []
    scale = 1024
    reverse = False
    reverseSignal = pyqtSignal(bool)
    rock = False
    time = None
    coordinates = "-"
    value = "-"
    xp = 0
    yp = 0
    zoom = [False, [-1, -1]] # [state (False, True), [start x, start y]
    changeZoom = pyqtSignal()
    pointerUpdate = pyqtSignal(str)
    crop = False
    crop_frame = None
    crop_time = None
    rotate = False

    def __init__(self, maps, clim=1000, w=640, h=480, cea=False, parent=None):
        self.clim = clim
        self.w = w
        self.h = h
        self.cea = cea
        self.max = len(maps)
        self.maps = maps

        for map in self.maps:
            map.pre_scale(self.scale)

        self.images = []
        self.im = []
        self.figs = []
        px = 1 / plt.rcParams['figure.dpi']
        plt.ioff()

        self.fig_width = self.w * px
        self.fig_height = self.h * px

        fig, _, im = self.maps[0].plot(clim=self.clim, cea=self.cea, scale=self.scale)
        fig.set_size_inches(self.fig_width, self.fig_height)
        fig.canvas.draw()
        self.figure = fig

        # pre-draws every frame
        for i in range(len(self.maps)):
            fig, _, im = self.maps[i].plot(clim=self.clim, cea=self.cea, scale=self.scale)
            fig.set_size_inches(self.fig_width, self.fig_height)
            self.figs.append(fig)
            fig.canvas.draw()
            self.im.append(im)

            image = fig.canvas.copy_from_bbox(fig.bbox)
            self.images.append(image)

        FigureCanvasQTAgg.__init__(self, self.figure)
        self.setParent(parent)
        self.player = Player(self)

        QTimer.singleShot(1000, self.startup)

    def startup(self):
        # everything breaks without these few lines even though it essentially does nothing; dont worry about it :)
        self.update_image(i=1)
        self.update_image(i=0)

        self.figure = self.figs[self.i]
        self.real = True
        self.connect_events()
        self.draw_idle()

        self.update_image(i=1)
        self.update_image(i=0)

    def connect_events(self):
        self.mpl_connect('button_press_event', self.click)
        self.mpl_connect('button_press_event', self.zoom_handler)
        self.mpl_connect('button_release_event', self.zoom_handler)
        self.mpl_connect('motion_notify_event', self.zoom_handler)
        self.mpl_connect('motion_notify_event', self.mouse_move)

    def start(self):
        self.running = True
        self.player.update_frame.connect(FigureCanvasQTAgg.blit)
        self.player.start()

    def cycle(self):
        # cycles through showing each image; should be run in a separate thread
        while self.running:
            self.update_image()
            self.cycle_process()
            time.sleep(self.speed)
            while self.paused:
                time.sleep(0.1)

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

    def update_image(self, i=None):
        if self.real:
            self.redraw()
        if i is not None:
            self.i = i
        self.restore_region(self.images[self.i])
        self.blit(self.figs[self.i].bbox)
        self.update_process(self.i)
        self.real = False
        self.time = str(self.maps[self.i].date)
        if self.xp is not None and self.yp is not None:
            self.value = self.maps[self.i].temp.data[int(self.xp + 0.5)][int(self.yp + 0.5)]
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

    def cycle_process(self):
        self.player.update_idx.emit(self.i)
        self.inc_i()

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

        self.figure = self.figs[self.i]

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
            self.figure = self.figs[self.i]
            self.real = True
            self.connect_events()
        self.im[self.i].set_clim(-clim, clim)
        self.clim = clim
        self.draw_idle()

    def toggle_reverse(self, val=None):
        if val is not None:
            self.reverse = val
        else:
            self.reverse = not self.reverse
            self.reverseSignal.emit(self.reverse)

    def mouse_move(self, event):
        if event.xdata is None:
            self.coordinates = "-"
            self.value = "-"
            self.xp = None
            self.yp = None
        else:
            try:
                self.coordinates = str(self.figure.axes[0].format_coord(event.xdata, event.ydata))
                self.value = self.maps[self.i].temp.data[int(event.ydata + 0.5)][int(event.xdata + 0.5)]
            except IndexError:
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
            self.draw_specific(self.i)
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
        self.restore_region(self.images[self.i])

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
        self.restore_region(self.images[self.i])
        self.blit()
        self.flush_events()
        self.zoom[0] = False
        self.changeZoom.emit()
        self.mode = None

        self.crop = True
        self.crop_frame = (self.zoom[1][0], self.zoom[1][1], event.xdata, event.ydata)
        self.crop_time = self.maps[self.i].date

        temp = self.maps[self.i].temp
        fig, _, im = self.maps[self.i].plot(clim=self.clim, cea=self.cea, scale=self.scale, crop=self.crop, frame=self.crop_frame)
        fig.set_size_inches(self.fig_width, self.fig_height)
        self.figure = fig
        self.real = True
        self.connect_events()
        self.draw_idle()
        self.maps[self.i].temp = temp #plotting changes temp, which is used for cutouts. If temp is changed and redraw is called, the image will be cropped aagain, essentially stacking crops
        self.im[self.i] = im

    def home(self):
        self.paused = True

        self.crop = False
        temp = self.maps[self.i].temp
        fig, _, im = self.maps[self.i].plot(clim=self.clim, cea=self.cea, scale=self.scale, crop=self.crop,
                                            frame=self.crop_frame)
        fig.set_size_inches(self.fig_width, self.fig_height)
        self.figure = fig
        self.real = True
        self.connect_events()
        self.draw_idle()
        self.maps[
            self.i].temp = temp  # plotting changes temp, which is used for cutouts. If temp is changed and redraw is called, the image will be cropped aagain, essentially stacking crops
        self.im[self.i] = im

    def set_zoom(self, val):
        if val:
            self.mode = 'zoom'
        else:
            self.mode = None

    def blit(self, bbox=None):
        self.player.update_frame.emit(
            self)  # blit function will be called from inside "Player" thread, so it must be overidden to signal a call from main thread

class Player(QThread):
    update_frame = pyqtSignal(object)
    update_idx = pyqtSignal(int)

    def __init__(self, canvas):
        super().__init__()
        self.canvas = canvas

    def run(self):
        self.canvas.cycle()

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

class Object(object):
    pass

class MoviePlayerQT(QWidget):

    i = 0

    def __init__(self, maps, **kwargs):
        super().__init__(**kwargs)

        self.len = len(maps)

        self.mainwidget = QWidget()
        self.setChildrenFocusPolicy(self.mainwidget, Qt.NoFocus)
        self.mainlayout = QVBoxLayout(self)
        self.layout = QGridLayout(self.mainwidget)
        self.setStyleSheet("QObject { background: white; }")
        self.mainlayout.addWidget(self.mainwidget)

        self.movie = Movie(maps)
        self.layout.addWidget(self.movie, 0, 0, 1, -1)
        self.start = self.movie.start

        #play/pause button
        self.pb = PlayButton()
        self.pb.clicked.connect(self.toggle)
        self.add_widget(self.pb)
        self.pb.setToolTip("Play/Pause")

        #back button
        self.bb = Button(icon=QIcon(':/movie-player/back.png'))
        self.bb.clicked.connect(lambda _: self.step(
            (self.movie.i - 1) % len(maps)))
        self.add_widget(self.bb)
        self.bb.setToolTip("Back")

        #forward button
        self.fb = Button(icon=QIcon(':/movie-player/forward.png'))
        self.fb.clicked.connect(lambda _: self.step(
            (self.movie.i + 1) % len(
                maps)))  # step is scaled based on speed multiplier
        self.add_widget(self.fb)
        self.fb.setToolTip("Forward")

        #play in reverse button
        self.rb = Button(icon=QIcon(':/movie-player/reverse.png'))
        self.rb.setCheckable(True)
        self.rb.clicked.connect(lambda _: self.movie.toggle_reverse(val=self.rb.isChecked()))
        self.movie.reverseSignal.connect(lambda val: self.rb.setChecked(val))
        self.add_widget(self.rb)
        self.rb.setToolTip("Play in Reverse")

        #rock/loop button
        self.rlb = Button(icon=QIcon(':/movie-player/rock.png'))
        self.rlb.setCheckable(True)
        self.rlb.clicked.connect(self.set_rock)
        self.add_widget(self.rlb)
        self.rlb.setToolTip("Rock/Loop")

        #home button
        self.hb = Button(icon=QIcon(':/movie-player/home.png'))
        self.hb.clicked.connect(self.movie.home)
        self.add_widget(self.hb)
        self.hb.setToolTip("Home")

        #crop button
        self.cb = Button(icon=QIcon(':/movie-player/crop.png'))
        self.cb.setCheckable(True)
        self.cb.clicked.connect(self.movie.set_zoom)
        self.add_widget(self.cb)
        self.cb.setToolTip("Zoom in")
        self.movie.changeZoom.connect(lambda: self.cb.setChecked(False))

        #track button
        self.tb = Button(icon=QIcon(':/movie-player/track.png'))
        self.tb.setCheckable(True)
        self.tb.clicked.connect(self.set_track)
        self.add_widget(self.tb)
        self.tb.setToolTip("Track zoomed location through movie")

        #speed slider
        self.ss = Slider(Qt.Horizontal)
        self.ss.setMinimum(-400)
        self.ss.setMaximum(400)
        self.ss.setValue(0)
        self.ss.sliderMoved.connect(self.update_speed)
        self.ss.setMinimumWidth(50)
        self.add_widget(self.ss)
        self.ss.setToolTip("Set Speed")

        #speed indicator
        self.si = QLabel()
        self.si.setText("1.00x")
        self.add_widget(self.si)
        self.si.setToolTip("Speed")

        #clipping range slider
        self.cs = Slider(Qt.Horizontal)
        self.cs.setMinimum(100)
        self.cs.setMaximum(1200)
        self.cs.setValue(self.movie.clim)
        self.cs.sliderMoved.connect(self.adjust_clim)
        self.cs.sliderMoved.connect(lambda val: self.ci.setText("%4dG" % (val)))
        self.cs.setMinimumWidth(50)
        self.add_widget(self.cs)
        self.cs.setToolTip("Adjust Clipping Values")

        #clipping indicator
        self.ci = QLabel()
        self.ci.setText("1000G")
        self.add_widget(self.ci)
        self.cs.setToolTip("Clipping Values")

        #pointer indicator
        self.pi = QLabel()
        self.add_widget(self.pi)
        self.pi.setToolTip("Time Location Value")
        self.movie.pointerUpdate.connect(lambda val: self.pi.setText(val))
        self.pi.setMinimumWidth(240)

        #progressbar
        self.sl = Slider(Qt.Horizontal)
        self.sl.setMinimum(0)
        self.sl.setMaximum(len(maps) - 1)
        self.sl.setValue(0)
        self.sl.setTickPosition(0)
        self.layout.addWidget(self.sl, 2, 0, 1, self.i)
        self.sl.sliderMoved.connect(self.slider)
        self.movie.player.update_idx.connect(self.update_slider)
        self.sl.setMaximumWidth(16777215)

        #trimming slider
        self.ts = RangeSlider(self.movie.max, Qt.Horizontal)
        self.ts.sliderMoved.connect(self.update_range)
        self.layout.addWidget(self.ts, 3, 0, 1, self.i)
        self.ts.setToolTip("Adjust Playback Range")

        #image label
        self.pl = QLabel()
        self.pl.setText(f'1/{len(maps)}')
        self.layout.addWidget(self.pl, 2, self.i)

        self.start()

    def setChildrenFocusPolicy(self, w, policy):
        def recursiveSetChildFocusPolicy(parentQWidget):
            for childQWidget in parentQWidget.findChildren(QWidget):
                childQWidget.setFocusPolicy(policy)
                recursiveSetChildFocusPolicy(childQWidget)

        recursiveSetChildFocusPolicy(w)

    def slider(self, val):
        self.toggle(True, state=True)
        self.movie.update_image(val)
        self.pl.setText(f'{val + 1}/{self.len}')

    def update_slider(self, i):
        self.pl.setText(f'{i + 1}/{self.len}')
        self.sl.setValue(i)

    def toggle(self, _, state=None):  # first parameter so that we can connect toggle to "update_slider"
        if state is not None:
            self.movie.paused = state
        else:
            self.movie.paused = (not self.movie.paused)

        self.pb.state(self.movie.paused)

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
        self.movie.speed = self.movie.basespeed / multiplier

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Space:
            self.toggle(None)
        elif event.key() == Qt.Key_Left:
            self.step((self.movie.i - max(1, int(self.movie.basespeed / self.movie.speed + 0.5))) % self.len)
        elif event.key() == Qt.Key_Right:
            self.step((self.movie.i + max(1, int(self.movie.basespeed / self.movie.speed + 0.5))) % self.len)

    def update_range(self, val):
        (min, max) = val
        self.movie.max = int(max + 1)
        self.movie.min = int(min)

    def add_widget(self, w):
        self.layout.addWidget(w, 1, self.i)
        self.i += 1

    def set_rock(self, val):
        self.movie.rock = val

    def adjust_clim(self, val):
        self.movie.adjust_clim(val)
        self.toggle(True, True)

    def set_track(self, val):
        self.movie.rotate = val