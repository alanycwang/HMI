from PyQt5.QtWidgets import *
import matplotlib.pyplot as plt
import movie, sys, pickle, time, warnings, util, search, projections
from PyQt5.QtCore import Qt
import sunpy.map
import astropy.time
import astropy.units as u


class AppQT(QMainWindow):
    def __init__(self):
        super().__init__()

        start = time.time()
        n = 20
        interval = 3*u.hour
        tstart = astropy.time.Time('2017-01-21T09:45:00', scale='utc', format='isot')
        tend = tstart + n*interval + 1*u.s
        maps = util.get_maps(tstart, tend, interval=interval, overwrite=True)
        maps = movie.MList(maps)
        maps.transform(projections.CylindricalEqualArea)
        with open('maps.pkl', 'wb') as fh:
            pickle.dump(maps, fh)
        print(time.time() - start)
        
        with open('maps.pkl', 'rb') as fh:
            maps = pickle.load(fh)

        # #checkerboard pattern for testing
        # for map in maps['hpc1024']:
        #     for i in range(1024):
        #         for j in range(1024):
        #             map.data[i][j] = (int(i/1024*3)*3 + int(j/1024*3)) * 1600 - 6400

        m = movie.MoviePlayerQT(maps)
        # print("Finished loading maps")

        # m = search.ARSearch()

        self.setWindowTitle("HMI")
        self.setCentralWidget(m)
        self.show()

def except_hook(cls, exception, traceback):
    sys.__excepthook__(cls, exception, traceback)

def set_proxy(proxy):
    import os
    os.environ['http_proxy'] = proxy 
    os.environ['HTTP_PROXY'] = proxy
    os.environ['https_proxy'] = proxy
    os.environ['HTTPS_PROXY'] = proxy
    os.environ['ftp_proxy'] = proxy
    os.environ['FTP_PROXY'] = proxy


if __name__ == '__main__':
    warnings.filterwarnings("ignore")

    set_proxy("http://proxy-zsgov.external.lmco.com:80")

    sys.excepthook = except_hook

    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    window = AppQT()
    sys.exit(app.exec_())

    # ar.update_ar_data()