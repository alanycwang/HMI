from PyQt5.QtCore import QThread, pyqtSignal, Qt, QSize, QTimer
from PyQt5.QtWidgets import *
from PyQt5.QtGui import QIcon
from superqt import QRangeSlider

class Slider(QSlider):
    s = """
    QSlider {
        height: 10px;
        margin: 5px
    }
    QSlider::groove:horizontal { 
        height: 10px; 
        margin-bottom: -10px; 
        background-color: rgb(150, 150, 150);
        border-radius: 5px; 
    }
    QSlider::handle:horizontal { 
        border: none; 
        height: 10px; 
        width: 10px; 
        margin: 0px; 
        border-radius: 5px; 
        background-color: rgb(70, 70, 105); 
    }
    QSlider::handle:horizontal:hover {
        background-color: rgb(50, 50, 85);
    }
    QSlider::groove:vertical { 
        height: 10px; 
        margin: 0px; 
        background-color: rgb(150, 150, 150);
        border-radius: 5px; 
    }
    QSlider::handle:vertical { 
        border: none; 
        height: 10px; 
        width: 10px; 
        margin: 0px; 
        border-radius: 5px; 
        background-color: rgb(70, 70, 105); 
    }
    QSlider::handle:vertical:hover {
        background-color: rgb(50, 50, 85);
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
            image: url(:/slider/pointer.png);
            width: 20px;
        }
        """

    def __init__(self, max, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setStyleSheet(self.ss)
        self.setMinimum(0)
        self.setMaximum(max - 1)
        self.setValue((0, max - 1))

class Button(QPushButton):
    s = """
            QPushButton { 
                border: none; 
                height: 20px; 
                width: 20px; 
                margin: 0px; 
                border-radius: 2px; 
                background-color: rgb(70, 70, 105); 
            }
            QPushButton::hover {
                background-color: rgb(50, 50, 85);
            }
            QPushButton::checked {
                background-color: rgb(30, 30, 65);
            }
            """

    def __init__(self, icon=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.setStyleSheet(self.s)
        if icon is not None: self.setIcon(icon)
        self.setIconSize(QSize(18, 18))

class PlayButton(Button):

	toggled = pyqtSignal(bool)
	paused = True

	def __init__(self, *args, **kwargs):
		self.pause = QIcon(':/movie-player/pause.png')
		self.play = QIcon(':/movie-player/play.png')

		super().__init__(self.play, *args, **kwargs)

		self.clicked.connect(self.toggle)

	def toggle(self, _, state=None):
		if state is not None:
			self.paused = state
		else:
			self.paused = (not self.paused)

		if self.paused:
			self.setIcon(self.play)
			self.setIconSize(QSize(18, 18))
		else:
			self.setIcon(self.pause)
			self.setIconSize(QSize(18, 18))

		self.toggled.emit(self.paused)