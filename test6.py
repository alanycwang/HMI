import sunpy.map
import util
import matplotlib.pyplot as plt
import astropy.units as u
from astropy.coordinates import SkyCoord

fig, ax = plt.subplots(2, 3)

# jsoc = sunpy.map.Map("/Users/awang/Documents/GitHub/HMI/data/hmi/JSOC_20220726_2033/hmi.sharp_cea_720s.8195.20220502_020000_TAI.magnetogram.fits")
jsoc = sunpy.map.Map("/Users/awang/Documents/GitHub/HMI/data/hmi/hmi.sharp_cea_720s.7001.20170430_080000_TAI.magnetogram.fits")
a = jsoc.meta.original_meta['ambngrow']

slice2, slice4 = jsoc.data.shape

ax[0, 0].imshow(jsoc.data[2:52, 0:50], cmap=plt.get_cmap('gray'), clim=(-500, 500))
ax[0, 0].set_title("hmi.sharp_cea_720s cutout (top left)")
ax[0, 0].grid(True)

ax[0, 1].imshow(jsoc.data[slice2 - 48:slice2 + 2, slice4 - 49:slice4 - 1], cmap=plt.get_cmap('gray'), clim=(-500, 500))
ax[0, 1].set_title("hmi.sharp_cea_720s cutout (bottom right)")
ax[0, 1].grid(True)

ax[0, 2].imshow(jsoc.data[2:, 2:-1], cmap=plt.get_cmap('gray'), clim=(-500, 500))
ax[0, 2].set_title("hmi.sharp_cea_720s cutout")
ax[0, 2].grid(True)

# m = "/Users/awang/Documents/GitHub/HMI/data/hmi/hmi.M_720s.20220502_020000_TAI.3.magnetogram.fits"
m = "/Users/awang/Documents/GitHub/HMI/data/hmi/hmi.M_720s.20170430_080000_TAI.3.magnetogram.fits"
m = sunpy.map.Map(m)

scale = jsoc.meta.original_meta['cdelt1']
print(scale, jsoc.meta.original_meta['cdelt2'])

bl = jsoc.wcs.pixel_to_world(0, slice2)
tr = jsoc.wcs.pixel_to_world(slice4, 0)

# jsoc.peek()
# raise Exception

# bl = SkyCoord(jsoc.meta.original_meta['londtmin'] * u.deg, jsoc.meta.original_meta['latdtmin'] * u.deg, frame=sunpy.coordinates.HeliographicStonyhurst)
# tr = SkyCoord(jsoc.meta.original_meta['londtmax'] * u.deg, jsoc.meta.original_meta['latdtmax'] * u.deg, frame=sunpy.coordinates.HeliographicStonyhurst)
center = SkyCoord(jsoc.meta.original_meta['crval1'] * u.deg, jsoc.meta.original_meta['crval2'] * u.deg, frame=jsoc.coordinate_frame)

# print(jsoc.date, m.date)

m = util.reproject_cea(m, coord=center, scale=scale, clip_h=False)
# m.peek()
# print(m.coordinate_frame) 
m = m.submap(bl, top_right=tr)
# print(bl, tr)
print(jsoc.data.shape, m.data.shape)

ax[1, 0].imshow(m.data[0:50, 2:52], cmap=plt.get_cmap('gray'), clim=(-500, 500))
ax[1, 0].set_title("hmi.m_720s reprojection (top left)")
ax[1, 0].grid(True)

ax[1, 1].imshow(m.data[slice2 - 50:slice2, slice4 - 48:slice4 + 2], cmap=plt.get_cmap('gray'), clim=(-500, 500))
ax[1, 1].set_title("hmi.m_720s reprojection (bottom right")
ax[1, 1].grid(True)

ax[1, 2].imshow(m.data[0:slice2 + 2, 0:slice4 + 2], cmap=plt.get_cmap('gray'), clim=(-500, 500))
ax[1, 2].set_title("hmi.m_720s reprojection")
ax[1, 2].grid(True)

plt.show()

