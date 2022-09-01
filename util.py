import sunpy.map, sunpy.io.fits
from sunpy.net import attrs as a
from sunpy.net import Fido, fido_factory

import astropy.time
import astropy.units as u
from astropy.coordinates import SkyCoord

import numpy as np
from operator import attrgetter
import requests, math

def set_proxy(proxy):
    import os
    os.environ['http_proxy'] = proxy 
    os.environ['HTTP_PROXY'] = proxy
    os.environ['https_proxy'] = proxy
    os.environ['HTTPS_PROXY'] = proxy
    os.environ['ftp_proxy'] = proxy
    os.environ['FTP_PROXY'] = proxy

#if no value for tend is provided, the function will return the image that was taken closest to time t. Otherwise, it will return images between t and tend
#interval determines the interval at which images are chosen. For example, if interval = 1 hour, it will pick images starting from t spaced out by 1 hour until it passes time tend
#if overwrite=False, get_maps will reuse data if it has already been downloaded before
#proxy automatically sets a proxy
#if m720s is True, get_maps will download from the hmi.m_720s series instead of hmi.m_45. Note that these images take significantly longer to download and require an interval > 720 seconds
#an email registered with JSOC is required to download from hmi.m_720s
def get_maps(t: astropy.time.Time, tend=None, interval=45 * u.s, overwrite=False, proxy=None, m720s=False, email=None):
    if proxy is not None:
        set_proxy(proxy)
    if tend is None or not isinstance(tend, astropy.time.Time): 
        tend = t + 22.5 * u.s
        t = t - 22.5 * u.s
    results = []

    #print(0)

    if not m720s:
        r = Fido.search(a.Time(t - 22.5 * u.s, tend + 22.5 * u.s), a.Instrument.hmi, a.Physobs.los_magnetic_field)
    else:
        r = Fido.search(a.Time(t - 360 * u.s, tend + 360 * u.s), a.jsoc.Series("hmi.m_720s"), a.jsoc.Notify(email))
    # print(r)
    #print(1)

    j = 0
    diff = math.inf
    for i in range(
            int((tend - t).to(u.s) / interval + 0.01)):  # find closest time to each given time requested, should be O(N)
        time = t + i * interval
        while True:  # iterate through all results to find closest time to given
            if not m720s:
                temp = astropy.time.Time(r[0]['Start Time'][j], scale='utc', format='isot')
            else:
                temp = astropy.time.Time(r[0]['T_REC'][j][0:-4].replace('.', '-').replace('_', 'T'), scale='utc', format='isot')
            if abs((temp - time).to(
                    u.s).value) > diff:  # stops when time difference begins to increase; picks last result
                diff = math.inf
                results.append(r[0][j - 1])
                j -= 1
                break
            diff = abs((temp - time).to(u.s).value)
            j += 1

    #print (2)
    #print(results)
    maps = []
    # fido starts downloading huge .tar files when you download too many files at the same time (this is very inefficient)
    for i in range(int(len(results)/8 + 0.9999)):
        # print("2" + str(i))
        r = fido_factory.UnifiedResponse(*tuple(results[i*8:min((i+1)*8, len(results))]))
        while True:
            try:
                #print(r)
                file = Fido.fetch(r, path=f"./data/hmi", max_conn=8, overwrite=overwrite)
            except requests.exceptions.ConnectionError:
                print("There was a a connection error: trying again...")
                continue
            break

        try:
            maps.extend(file)
        except OSError:  # in case the existing file is broken
            # except connection error again
            while True:
                try:
                    file = Fido.fetch(r, path=f"./data/hmi", max_conn=8, overwrite=overwrite)
                except requests.exceptions.ConnectionError:
                    continue
                break
            maps.extend(file)

    #print(3)


    if not isinstance(maps, list):
        maps = [maps]
    # for i in range(len(maps)):
    #     maps[i] = maps[i].rotate(order=3)

    temp = []
    for map in maps:
        temp.append(sunpy.map.Map(map))
    temp = sorted(temp, key=attrgetter('date')) # for some reason the array ends up out of chronological order
    #print(temp)
    if len(temp) == 1: return temp[0]
    if len(temp) == 0: return None
    #print(4)
    return temp

#flattens list 
#for example: flatten([1, 2, 3, [3, [[2], 3, 1]]]) returns [1, 2, 3, 3, 2, 3, 1]
def flatten(lst):
    res = []

    for item in lst:
        if type(item) is list:
            res.extend(flatten(item))
        else:
            res.append(item)

    return res

#takes a value within in_range and scales it to out_range using its relative position inside of in_range
#for example, scale(2, (0, 10), (50, 100)) returns 60
def scale(val, in_range: tuple, out_range: tuple):
    in_min, in_max = in_range
    out_min, out_max = out_range
    return out_min + (val - in_min)*((out_max - out_min)/(in_max - in_min))

#differentially rotates a given point determined by a rotation time
#the coordinate returned will be heliographic by default, so out_frame can be provided if otherwise required
def rotate(point, duration, out_frame=None):
    #sunpy for some reason uses its own coordinate system instead of SkyCoord when differentially rotating a point, which means we will have to do this ourselves
    if duration.value == 0:
        return point
    transformed = point.transform_to(sunpy.coordinates.HeliographicStonyhurst) #1: get heliographic coordinates
    w = (14.713 + -2.396*(math.sin(transformed.lat.degree)**2) + -1.787*(math.sin(transformed.lat.degree)**4)) * u.degree/u.day #2: get angular velocity at longitude (https://en.wikipedia.org/wiki/Solar_rotation)
    new = SkyCoord(transformed.lon.degree*u.degree + w*duration, transformed.lat.degree*u.degree, frame=sunpy.coordinates.HeliographicStonyhurst, obstime=point.obstime) #3: create new coordinate using w
    if out_frame is not None: 
        return new.transform_to(out_frame)
    else: return new

#slices a 2d array/image from xmin to xmax and ymin to ymax
#if any of the parameters exceeds the bounds of the array, extra zeros will be added to preserve the aspect ratio
def slice_extend(arr, xmin, xmax, ymin, ymax):
    # print(arr.shape, xmin, xmax, ymin, ymax)
    w, h = arr.shape
    diffs = [0 - xmin, xmax - w, 0 - ymin, ymax - h]
    new = arr[max(0, xmin):min(w, xmax), max(0, ymin):min(h, ymax)]
    if diffs[0] > 0:
        new = np.append(np.zeros((diffs[0], h)), new, axis=0)
        w += diffs[0]
    if diffs[1] > 0:
        new = np.append(new, np.zeros((diffs[1], h)), axis=0)
        w += diffs[1]
    if diffs[2] > 0:
        new = np.append(np.zeros((w, diffs[2])), new, axis=1)
    if diffs[3] > 0:
        new = np.append(new, np.zeros((w, diffs[3])), axis=1)
    return new

