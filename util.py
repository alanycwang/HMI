import sunpy.map, sunpy.io.fits
from sunpy.net import attrs as a
from sunpy.net import Fido, fido_factory

import astropy.time
import astropy.units as u

from operator import attrgetter
from magnetogram import Magnetogram
import requests, math

def get_maps(t: astropy.time.Time, tend=None, interval=45 * u.s, gen_magnetogram=False, overwrite=False):
    if tend is None or not isinstance(tend, astropy.time.Time): tend = t + 45 * u.s
    results = []

    print(0)

    r = Fido.search(a.Time(t - 22.5 * u.s, tend + 22.5 * u.s), a.Instrument.hmi, a.Physobs.los_magnetic_field)

    print(1)

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

    print (2)

    maps = []
    # fido starts downloading huge .tar files when you download too many files at the same time (this is very inefficient)
    for i in range(int(len(results)/8 + 1)):
        print("2" + str(i))
        r = fido_factory.UnifiedResponse(*tuple(results[i*8:min((i+1)*8, len(results))]))
        while True:
            try:
                file = Fido.fetch(r, path=f"./data/hmi", max_conn=8, overwrite=overwrite)
            except requests.exceptions.ConnectionError:
                print("There was a a connection error: trying again...")
                continue
            break

        try:
            maps.extend(sunpy.map.Map(file))
        except OSError:  # in case the existing file is broken
            # except connection error again
            while True:
                try:
                    file = Fido.fetch(r, path=f"./data/hmi", max_conn=8, overwrite=overwrite)
                except requests.exceptions.ConnectionError:
                    continue
                break
            maps.extend(sunpy.map.Map(file))

    print(3)


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
    print(4)
    return temp

def flatten(lst):
    res = []

    for item in lst:
        if type(item) is list:
            res.extend(flatten(item))
        else:
            res.append(item)

    return res