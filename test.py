import sunpy.map, time
from astropy.coordinates import SkyCoord
import astropy.units as u

jsoc = sunpy.map.Map("/Users/awang/Documents/GitHub/HMI/data/hmi/hmi.sharp_cea_720s.7001.20170430_080000_TAI.magnetogram.fits")

start = time.time()
for i in range(90):
    for j in range(90):
        #print(i*90+j)
        #c = SkyCoord(i*u.deg, j*u.deg, frame=jsoc.coordinate_frame)
        a = jsoc.wcs.world_to_pixel_values([i*u.deg, j*u.deg])
        #print(a)
print(time.time() - start)