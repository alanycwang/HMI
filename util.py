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
    var = {} #dictionary of versions (helioprojective, helioprojective zoomed, heliographic, heliographic zoomed)

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
        if self.temp_scale == self.scale:
            return
        self.rescaled = self.map.resample([scale, scale]*u.pix)
        self.temp_scale = scale

    def plot(self, clim=1000, cea=False, scale=4096, crop=False, frame=None, rot=False, start_time=None, skip_reset=False):
        #must either graph cea, crop, or scale. Cannot do all three at once
        p = self.map
        type = 'helioprojective'
        if cea:
            if self.cea is None:
                self.gen_cea()
            p = self.cea
            type = 'heliographic'
        if crop:
            temp = self.map
            if cea:
                if self.cea is None:
                    self.gen_cea()
                temp = self.cea
            p = self.crop(temp, *frame, rot=rot, start_time=start_time, cea=cea)
            type += ' zoomed'
        if not cea and not crop and scale != 4096:
            if scale == self.temp_scale:
                p = self.rescaled
            else:
                self.pre_scale(scale)
                return self.plot(clim=clim, cea=cea, scale=scale, crop=crop, frame=frame, rot=rot, start_time=start_time)
        if not skip_reset: self.var[type] = p
        fig = plt.figure()
        ax = plt.subplot(projection=p)
        im = p.plot(ax)
        im.set_clim(-clim, clim)

        return fig, ax, im

    def crop(self, map, top_right, bottom_left, rot=False, start_time=None, cea=False):
        unit = u.arcsec
        a = ['Tx', 'Ty', 'arcsec']
        if cea:
            unit = u.degree
            a = ['lon', 'lat', 'degree']

        center = SkyCoord((getattr(getattr(top_right, a[0]), a[2]) + getattr(getattr(bottom_left, a[0]), a[2]))/2 * unit, (getattr(getattr(top_right, a[1]), a[2]) + getattr(getattr(bottom_left, a[1]), a[2]))/2 * unit, frame=map.coordinate_frame)
        if rot and start_time is not None: center = rotate(self.map, center, (self.date - start_time).to(u.day))
        w = getattr(getattr(top_right, a[0]), a[2]) - getattr(getattr(bottom_left, a[0]), a[2])

        top_right = SkyCoord((center.Tx.arcsec + w/2) * unit, getattr(getattr(top_right, a[1]), a[2]) * unit, frame=self.map.coordinate_frame)
        bottom_left = SkyCoord((getattr(getattr(top_right, a[0]), a[2]) - w) * unit, getattr(getattr(bottom_left, a[1]), a[2]) * unit, frame=self.map.coordinate_frame)

        return map.submap(bottom_left, top_right=top_right)


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

def flatten(lst):
    res = []

    for item in lst:
        if type(item) is list:
            res.extend(flatten(item))
        else:
            res.append(item)

    return res