import astropy.time
import astropy.units as u
from astropy.io import fits

import matplotlib.pyplot as plt

from skimage.transform import resize

class Magnetogram():
    def __init__(self, file, time: astropy.time.Time):
        with fits.open(file) as hdul:
            header = hdul[1].header
            self.time = time
            self.data = hdul[1].data

    def plot(self, ax, res=(4096, 4096), **kwargs):
        kwargs['cmap'] = kwargs.get('cmap', plt.get_cmap('gray'))
        kwargs['origin'] = kwargs.get('origin', 'lower')
        data = resize(self.data, res)

        fig, ax = plt.subplots()
        im = ax.imshow(data, **kwargs)
        return fig, ax, im

    def peek(self, **kwargs):
        fig, ax, im = self.plot(**kwargs)
        fig.colorbar(im)
        plt.show()
