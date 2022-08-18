import sys
import os
current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

import astropy.time
import astropy.units as u

from util import get_maps



tstart = astropy.time.Time('2022-01-21T09:45:00', scale='utc', format='isot')
tend = tstart + 1 * u.day + 90 * u.minute

maps = get_maps(tstart, tend=tend, interval=3 * u.hour, proxy="http://proxy-zsgov.external.lmco.com:80")
for map in maps:
    print(map.date)

print("done")