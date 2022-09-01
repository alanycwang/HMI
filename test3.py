import sunpy.map
import numpy as np
from astropy.coordinates import SkyCoord
import astropy.units as u
import time

map = sunpy.map.Map("hmi.M_45s.20220819_235315_TAI.2.magnetogram.fits")

start = time.time()
h = 4096
w = int(4096*np.pi + 0.5)
header = sunpy.map.make_fitswcs_header(
    (h, w),
    SkyCoord(0, 0, unit=u.deg, frame="heliographic_stonyhurst", obstime=map.date, rsun=map.coordinate_frame.rsun),
    scale=(360/w, 360/w)*u.deg/u.pix, 
    projection_code="CEA")
map = map.reproject_to(header)
print(time.time() - start)
map.peek()