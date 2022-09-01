import astropy.units as u
from astropy.coordinates import SkyCoord
import math
import sunpy.coordinates

def rotate(point, duration):
    #sunpy method is stupid, so try rotating with astropy
    if duration.value == 0:
        return point
    transformed = point
    w = (14.713 + -2.396*(math.sin(transformed.lat.degree)**2) + -1.787*(math.sin(transformed.lat.degree)**4)) * u.degree/u.day #2: get angular velocity at longitude (https://en.wikipedia.org/wiki/Solar_rotation)
    new = SkyCoord(transformed.lon.degree*u.degree + w*duration, transformed.lat.degree*u.degree, frame=sunpy.coordinates.HeliographicStonyhurst) #3: create new coordinate using w
    return new