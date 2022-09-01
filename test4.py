import util, sunpy.map
import astropy.time
import astropy.units as u
import time, projections

m = sunpy.map.Map("/Users/awang/Documents/GitHub/HMI/data/hmi/hmi.M_720s.20170430_080000_TAI.3.magnetogram.fits")

start = time.time()
t = projections.CylindricalEqualArea.from_hpc(m, scale=0.0299999993*2)
print("interpolation: " + str(time.time() - start))