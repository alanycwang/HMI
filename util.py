import sunpy.map, sunpy.io.fits
from sunpy.coordinates import RotatedSunFrame
from sunpy.net import Fido, fido_factory
from sunpy.net import attrs as a

import astropy.time
import astropy.units as u
from astropy.coordinates import SkyCoord

import numpy as np
from operator import attrgetter
import matplotlib.pyplot as plt
import requests, math

class Magnetogram():

    cea = None
    rescaled = None
    temp_scale = None
    date = None
    temp = None # version that is currently "active" in movie player

    def __init__(self, map, scale=4096):
        self.scale = scale
        if scale != 4096:
            self.map = map.resample([scale, scale]*u.pix)
        else: self.map = map
        self.date = self.map.date

    def gen_cea(self):
        shape_out = (720, 1440)
        frame_out = SkyCoord(0, 0, unit=u.deg, frame="heliographic_stonyhurst", obstime=self.map.date, rsun=self.map.coordinate_frame.rsun)
        header = sunpy.map.make_fitswcs_header(shape_out, frame_out, scale=(360 / shape_out[1], 120 / shape_out[0]) * u.deg / u.pix, projection_code="CEA")
        self.cea = self.map.reproject_to(header)

    def pre_scale(self, scale):
        self.rescaled = self.map.resample([scale, scale]*u.pix)
        self.temp_scale = scale

    def plot(self, clim=1000, cea=False, scale=4096, crop=False, frame=(0, 0, 4096, 4096), rot=False, start_time=None):
        #must either graph cea, crop, or scale. Cannot do all three at once
        p = self.map
        if cea:
            if self.cea is None:
                self.gen_cea()
            p = self.cea
        elif crop:
            p = self.crop(*frame, rot=rot, start_time=start_time)
        elif scale != 4096:
            if scale == self.temp_scale:
                p = self.rescaled
            else:
                self.pre_scale(scale)
                return self.plot(clim=clim, cea=cea, scale=scale)
        self.temp = p
        fig = plt.figure()
        ax = plt.subplot(projection=p)
        im = p.plot(ax)
        im.set_clim(-clim, clim)

        return fig, ax, im

    def crop(self, x1, y1, x2, y2, rot=False, start_time=None):
        wcs = self.temp.wcs
        top_right = wcs.pixel_to_world(max(x1, x2), max(y1, y2))
        bottom_left = wcs.pixel_to_world(min(x1, x2), min(y1, y2))

        if rot and start_time is not None:
            center = SkyCoord((top_right.Tx.arcsec + bottom_left.Tx.arcsec)/2 * u.arcsec, (top_right.Ty.arcsec + bottom_left.Ty.arcsec)/2 * u.arcsec, frame=self.temp.coordinate_frame)
            center = rotate(self.map, center, (self.map.date - start_time).to(u.day))
            w = top_right.Tx.arcsec - bottom_left.Tx.arcsec

            top_right = SkyCoord((center.Tx.arcsec + w/2) * u.arcsec, top_right.Ty.arcsec * u.arcsec, frame=self.temp.coordinate_frame)
            bottom_left = SkyCoord((top_right.Tx.arcsec - w) * u.arcsec, bottom_left.Ty.arcsec * u.arcsec, frame=self.temp.coordinate_frame)

        return self.map.submap(bottom_left, top_right=top_right)


def get_maps(t: astropy.time.Time, tend=None, interval=45 * u.s, gen_magnetogram=False):
    if tend is None or not isinstance(tend, astropy.time.Time): tend = t + 45 * u.s
    results = []

    r = Fido.search(a.Time(t - 22.5 * u.s, tend + 22.5 * u.s), a.Instrument.hmi, a.Physobs.los_magnetic_field)

    j = 0
    diff = math.inf
    for i in range(
            int((tend - t).to(u.s) / interval)):  # find closest time to each given time requested, should be O(N)
        time = t + i * interval
        while True:  # iterate through all results to find closest time to given
            temp = astropy.time.Time(r[0]['Start Time'][j], scale='utc', format='isot')
            if abs((temp - time).to(
                    u.s).value) > diff:  # stops when time difference begins to increase; picks last result
                diff = math.inf
                results.append(r[0][j - 1])
                j -= 1
                break
            diff = abs((temp - time).to(u.s).value)
            j += 1

    results = fido_factory.UnifiedResponse(*tuple(results))

    # in case of connection error, try again
    while True:
        try:
            file = Fido.fetch(results, path=f"./data",
                              overwrite=False)  # so that we don't download the same thing twice
        except requests.exceptions.ConnectionError:
            continue
        break

    try:
        maps = sunpy.map.Map(file)
    except OSError:  # in case the existing file is broken
        # except connection error again
        while True:
            try:
                file = Fido.fetch(results, path=f"./data", overwrite=True)
            except requests.exceptions.ConnectionError:
                continue
            break
        maps = sunpy.map.Map(file)


    if not isinstance(maps, list):
        maps = [maps]
    for i in range(len(maps)):
        maps[i] = maps[i].rotate(order=3)

    temp = maps
    if gen_magnetogram:
        temp = []
        for map in maps:
            temp.append(Magnetogram(map))
    temp = sorted(temp, key=attrgetter('date')) # for some reason the array ends up out of chronological order

    if len(temp) == 1: return temp[0]
    return temp

def get_cutouts(maps, x1, x2, y1, y2, recenter=True):  #will adjust cutout location according to solar rotation
    new = []
    for map in maps:
        c1 = SkyCoord(x1, y1, frame=map.coordinate_frame)
        c2 = SkyCoord(x2, y2, frame=map.coordinate_frame)
        new.append(map.submap(c1, c2))

def get_ar_data(tstart: astropy.time.Time, tend: astropy.time.Time):  # WIP
    result = Fido.search(a.Time(tstart, tend), a.hek.EventType('AR'))
    for key in result['hek'].keys():
        print(key, result['hek'][key][0])

def rotate(map, point, duration):
    #sunpy method is stupid, so try rotating with astropy
    if duration.value == 0:
        return point

    transformed = point.transform_to(sunpy.coordinates.HeliographicStonyhurst) #1: get heliographic coordinates
    w = (14.713 + -2.396*(math.sin(transformed.lat.degree)**2) + -1.787*(math.sin(transformed.lat.degree)**4)) * u.degree/u.day #2: get angular velocity at longitude (https://en.wikipedia.org/wiki/Solar_rotation)
    new = SkyCoord(transformed.lon.degree*u.degree + w*duration, transformed.lat.degree*u.degree, frame=sunpy.coordinates.HeliographicStonyhurst) #3: create new coordinate using w
    return new.transform_to(map.coordinate_frame)