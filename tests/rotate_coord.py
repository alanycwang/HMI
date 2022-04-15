import astropy.time
import astropy.units as u
from astropy.coordinates import SkyCoord
import sunpy.coordinates
from sunpy.coordinates import RotatedSunFrame
import util
import math
import matplotlib.pyplot as plt

map = util.get_maps(astropy.time.Time('2022-01-21T09:45:00', scale='utc', format='isot'))

t = 1*u.day

coord = SkyCoord(200*u.arcsec, 400*u.arcsec, frame=map.coordinate_frame)
coord = coord.transform_to(sunpy.coordinates.HeliographicStonyhurst)

w = (14.713 + -2.396*(math.sin(coord.lat.degree)**2) + -1.787*(math.sin(coord.lat.degree)**4)) * u.degree/u.day #https://en.wikipedia.org/wiki/Solar_rotation
new_coord = SkyCoord(coord.lon.degree*u.degree + w*t, coord.lat.degree*u.degree, frame=sunpy.coordinates.HeliographicStonyhurst)
new_coord = new_coord.transform_to(map.coordinate_frame)

rotated = RotatedSunFrame(base=coord, duration=t)
rotated = rotated.transform_to(map.coordinate_frame)

fig = plt.figure()
ax = fig.add_subplot(projection=map)
map.plot(axes=ax)
ax.plot_coord(coord, 'o', color='r')
ax.plot_coord(new_coord, 'o', color='b')
ax.plot_coord(rotated, 'o', color='g')
plt.show()