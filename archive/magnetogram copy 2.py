import astropy.time
from astropy.io import fits

import numpy as np

class Magnetogram():

	date = astropy.time.Time('1971-01-1T00:00:00', scale='utc', format='isot')
	data = np.array([[None]])
	header = {}


	def __init__(self, file):
		with fits.open(file) as hdul:
			hdul.verify('fix')
			h = hdul[1].header
			for key, val in h.items():
				self.header[key] = val #cannot pickle astropy CompImageHeader - must convert to dict first

			self.data = hdul[1].data

		self.date = astropy.time.Time(self.header['DATE-OBS'])