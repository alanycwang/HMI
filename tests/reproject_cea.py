import sunpy.map
from sunpy.net import Fido
from sunpy.net import attrs as a

import astropy.units as u
from astropy.coordinates import SkyCoord
from astropy.wcs import WCS

import matplotlib.pyplot as plt

if __name__ == '__main__':
    result = Fido.search(a.Time('2020/01/20 00:00:00', '2020/01/20 00:01:00'), a.Instrument.hmi, a.Physobs.los_magnetic_field)
    jsoc_result = result[0]
    fh = Fido.fetch(result)
    m = sunpy.map.Map(fh[0])
    m = m.rotate(order=3)

    print(type(m))

    shape_out = (720, 1440)
    frame_out = SkyCoord(0, 0, unit=u.deg,
                         frame="heliographic_stonyhurst",
                         obstime=m.date,
                         rsun=m.coordinate_frame.rsun)
    header = sunpy.map.make_fitswcs_header(shape_out,
                                           frame_out,
                                           scale=(360 / shape_out[1],
                                                  120 / shape_out[0]) * u.deg / u.pix,
                                           projection_code="CEA")
    m = m.reproject_to(header)
    m.peek()




