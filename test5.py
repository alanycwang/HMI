import sunpy.map
import util
import matplotlib.pyplot as plt
import astropy.units as u
from astropy.coordinates import SkyCoord

fig, ax = plt.subplots(2, 3)

# jsoc = sunpy.map.Map("/Users/awang/Documents/GitHub/HMI/data/hmi/JSOC_20220726_2033/hmi.sharp_cea_720s.8195.20220502_020000_TAI.magnetogram.fits")
jsoc = sunpy.map.Map("/Users/awang/Documents/GitHub/HMI/data/hmi/hmi.sharp_cea_720s.7001.20170430_080000_TAI.magnetogram.fits")
a = jsoc.meta.original_meta['ambngrow']

scale = jsoc.meta.original_meta['cdelt1']
print(scale, jsoc.meta.original_meta['cdelt2'])