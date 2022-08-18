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

def flatten(lst):
    res = []

    for item in lst:
        if type(item) is list:
            res.extend(flatten(item))
        else:
            res.append(item)

    return res

def rotate(map, point, duration, type='hpc'):
    #sunpy method is stupid, so try rotating with astropy
    if duration.value == 0:
        return point
    if type == 'hpc': transformed = point.transform_to(sunpy.coordinates.HeliographicStonyhurst) #1: get heliographic coordinates
    else: transformed = point
    w = (14.713 + -2.396*(math.sin(transformed.lat.degree)**2) + -1.787*(math.sin(transformed.lat.degree)**4)) * u.degree/u.day #2: get angular velocity at longitude (https://en.wikipedia.org/wiki/Solar_rotation)
    new = SkyCoord(transformed.lon.degree*u.degree + w*duration, transformed.lat.degree*u.degree, frame=sunpy.coordinates.HeliographicStonyhurst) #3: create new coordinate using w
    if type == 'hpc': return new.transform_to(map.coordinate_frame)
    else: return new

def scale(val, in_range: tuple, out_range: tuple):
    in_min, in_max = in_range
    out_min, out_max = out_range
    return out_min + (val - in_min)*((out_max - out_min)/(in_max - in_min))

def reproject_cea(m, coord=None, w=4096, origin_x=0, origin_y=0, clip_h=True, frame="heliographic_stonyhurst", scale=None):
    if scale is not None:
        w = int(360/scale + 0.5)
    else:
        scale = 360/w
    h=w/np.pi
    if coord is None:
        frame_out = SkyCoord(origin_x, origin_y, unit=u.deg, frame=frame, obstime=m.date, rsun=m.coordinate_frame.rsun)
    else:
        frame_out = coord
    if clip_h:
        h = int(h + 4 - h%4) #make sure it's divisible by 4 for easier downscaling
    else:
        h = int(h + 0.5)
    header = sunpy.map.make_fitswcs_header((h, w), frame_out, scale=(scale, scale)*u.deg/u.pix, projection_code="CEA") #since the deg/pix ratio for lattitude is not linear, giving the correct ratio makes the projection overcompensate for nonlinearity
    return m.reproject_to(header)

def rotate(map, point, duration, type='hpc'):
    #sunpy method is stupid, so try rotating with astropy
    if duration.value == 0:
        return point
    if type == 'hpc': transformed = point.transform_to(sunpy.coordinates.HeliographicStonyhurst) #1: get heliographic coordinates
    else: transformed = point
    w = (14.713 + -2.396*(math.sin(transformed.lat.degree)**2) + -1.787*(math.sin(transformed.lat.degree)**4)) * u.degree/u.day #2: get angular velocity at longitude (https://en.wikipedia.org/wiki/Solar_rotation)
    new = SkyCoord(transformed.lon.degree*u.degree + w*duration, transformed.lat.degree*u.degree, frame=sunpy.coordinates.HeliographicStonyhurst) #3: create new coordinate using w
    if type == 'hpc': return new.transform_to(map.coordinate_frame)
    else: return new