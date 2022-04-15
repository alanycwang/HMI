import astropy.time
import astropy.units as u

import util



tstart = astropy.time.Time('2022-01-21T09:45:00', scale='utc', format='isot')
tend = tstart + 1 * u.day + 90 * u.minute

maps = util.get_maps(tstart, tend=tend, interval=3 * u.hour)
for map in maps:
    print(map.date)