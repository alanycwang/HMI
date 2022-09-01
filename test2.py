from turtle import goto
from astropy.io import fits
import pyqtgraph as pg
import sunpy.map
import astropy.units as u
from astropy.coordinates import SkyCoord
import numpy as np
from PyQt5.QtWidgets import *
import sys, util, math, sunpy, pickle
from PyQt5.QtCore import QRectF

# with open('maps.pkl', 'rb') as fh:
#     maps = pickle.load(fh)

# cea = maps.getData(cea4096)[0]

class AspectRatioWidget(QWidget):
    """A widget that will maintain a specified aspect ratio.
    Good for plots where we want to fill the maximum space without stretching the aspect ratio."""

    def __init__(self, widget, aspect_ratio, parent=None):
        super().__init__(parent)
        self.aspect_ratio = aspect_ratio
        self.setLayout(QBoxLayout(QBoxLayout.LeftToRight, self))
        self.layout().addItem(QSpacerItem(0, 0))
        self.layout().addWidget(widget)
        self.layout().addItem(QSpacerItem(0, 0))

    def setAspectRatio(self, aspect_ratio):
        self.aspect_ratio = aspect_ratio
        self._adjust_ratio(self.geometry().width(), self.geometry().height());

    def resizeEvent(self, e):
        self._adjust_ratio(e.size().width(), e.size().height())

    def _adjust_ratio(self, w, h):
        if w / h > self.aspect_ratio:  # too wide
            self.layout().setDirection(QBoxLayout.LeftToRight)
            widget_stretch = h * self.aspect_ratio
            outer_stretch = (w - widget_stretch) / 2 + 0.5
        else:  # too tall
            self.layout().setDirection(QBoxLayout.TopToBottom)
            widget_stretch = w / self.aspect_ratio
            outer_stretch = (h - widget_stretch) / 2 + 0.5

        self.layout().setStretch(0, outer_stretch)
        self.layout().setStretch(1, widget_stretch)
        self.layout().setStretch(2, outer_stretch)

jsoc = sunpy.map.Map("/Users/awang/Documents/GitHub/HMI/data/hmi/JSOC_20220726_2033/hmi.sharp_cea_720s.8195.20220502_020000_TAI.magnetogram.fits")

jsoc_data = np.flip(np.rot90(jsoc.data), axis=0)
# jsoc_data = jsoc.data

app = QApplication(sys.argv)
app.setStyle('Fusion')
window = QMainWindow()

gv = pg.GraphicsView(useOpenGL=True)
mw = AspectRatioWidget(gv, len(jsoc_data)/len(jsoc_data[0]))
gl = pg.GraphicsLayout()
gv.setCentralItem(gl)
plot = gl.addPlot()
plot.setAspectLocked(lock=True)
plot.setMouseEnabled(x=False, y=False)
plot.setMenuEnabled(enableMenu=False)
plot.setDefaultPadding(padding=0)
img = pg.ImageItem()
img.setLevels([-1000, 1000])
img.setImage(jsoc_data)
plot.addItem(img)
print(plot.getViewBox().screenGeometry().height())
print(gv.geometry().height())
print(plot.getViewBox().screenGeometry().width())
print(gv.geometry().width())
mw.setAspectRatio((len(jsoc_data) - plot.getViewBox().screenGeometry().width() + gv.geometry().width())/(len(jsoc_data[0]) - plot.getViewBox().screenGeometry().height() + gv.geometry().height()))
print(mw.aspect_ratio)

#choose tick interval
hp, wp = jsoc.data.shape #height and width in pixels
bl = jsoc.wcs.pixel_to_world(0, 0).transform_to(sunpy.coordinates.HeliographicStonyhurst)
tr = jsoc.wcs.pixel_to_world(wp, hp).transform_to(sunpy.coordinates.HeliographicStonyhurst)
# print(bl, tr)
plot.getViewBox().setRange(QRectF(0, 0, wp, hp), disableAutoRange=True)

#fix image frame

#calculate height and width in degrees
hd = tr.lat.degree - bl.lat.degree
wd = tr.lon.degree - bl.lon.degree

#maximum 5 lines before switching to higher level of spacing
#hi = latitude tick interval
#wi = longitude tick interval
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

#choose tick latitudes/longitudes and set ticks
yticks = []
for i in range(-2, int(hd/hi + 0.5) + 2):
    yticks.append(bl.lat.degree - bl.lat.degree%hi + hi*(i + 1))
# temp = jsoc.wcs.world_to_pixel(SkyCoord([0*u.degree]*len(yticks), yticks*u.degree, frame=jsoc.coordinate_frame))
# print(temp)
# print(type(temp))
# gv.plot.getAxis('left').setTicks([yticks])
xticks = []
for i in range(-2, int(wd/wi + 0.5) + 2):
    xticks.append(bl.lon.degree - bl.lon.degree%wi + wi*(i + 1))

print(yticks, xticks)

#calculate point locations (one per 10, 5, or 1 degree depending on scale)
xpts = []
for i in range(len(xticks) - 1):
    xpts.extend(np.linspace(xticks[i], xticks[i + 1], num=5).tolist())
xpts.append(xticks[-1])

ypts = []
for i in range(len(yticks) - 1):
    ypts.extend(np.linspace(yticks[i], yticks[i + 1], num=5).tolist())
ypts.append(yticks[-1])


#draw spline with points
xtickpixels = []
for i, x in enumerate(xticks):
    pos = False
    low = True
    pts = []
    for j, y in enumerate(ypts):
        xp, yp = jsoc.wcs.world_to_pixel(SkyCoord(x*u.degree, y*u.degree, frame=sunpy.coordinates.HeliographicStonyhurst))
        if xp >= 0 and xp < wp and yp >= 0 and yp < hp:
            pos = True
        if low and yp > 0:
            pts = [pts[-1]]
            xtickpixels.append((xp - yp*(xp - pts[0][0])/(yp - pts[0][1]), str(int(x))))
            low = False
        pts.append([xp, yp])
        if yp > hp:
            break
    if not pos: continue
    line = pg.PlotDataItem(np.array(pts), antialias=True)
    plot.addItem(line)

ytickpixels = []
for j, y in enumerate(yticks):
    pos = False
    low = True
    pts = []
    for i, x in enumerate(xpts):
        xp, yp = jsoc.wcs.world_to_pixel(SkyCoord(x*u.degree, y*u.degree, frame=sunpy.coordinates.HeliographicStonyhurst))
        if xp >= 0 and xp < wp and yp >= 0 and yp < hp:
            pos = True
        if low and xp > 0:
            pts = [pts[-1]]
            ytickpixels.append((yp - xp*(yp - pts[0][1])/(xp - pts[0][0]), str(int(y))))
            low = False
        pts.append([xp, yp])
        if xp > wp:
            break
    if not pos: continue
    line = pg.PlotDataItem(np.array(pts), antialias=True)
    plot.addItem(line)

    
plot.getAxis('left').setTicks([ytickpixels])
plot.getAxis('bottom').setTicks([xtickpixels])

window.setCentralWidget(mw)
window.show()

sys.exit(app.exec_())