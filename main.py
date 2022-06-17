from PyQt5.QtWidgets import *
import matplotlib.pyplot as plt
import astropy.units as u
import astropy.time
import movie, util, sys, pickle, time, warnings, magnetogram, ar, search
from PyQt5.QtCore import Qt


class AppQT(QMainWindow):
    def __init__(self):
        super().__init__()

        # maps = pickle.load(open("./data/maps.pkl", "rb"))
        # maps = [magnetogram.Magnetogram(map) for map in maps]

        # n = 20
        # interval = 3*u.hour

        # tstart = astropy.time.Time('2017-01-21T09:45:00', scale='utc', format='isot')
        # tend = tstart + n*interval
        # maps = util.get_maps(tstart, tend, interval=interval, gen_magnetogram=True, overwrite=True)
        #
        # m = movie.MoviePlayerQT(maps)
        # print("Finished loading maps")

        m = search.ARSearch()

        self.setWindowTitle("HMI")
        self.setFixedSize(m.sizeHint())
        self.setCentralWidget(m)
        self.show()

def except_hook(cls, exception, traceback):
    sys.__excepthook__(cls, exception, traceback)

if __name__ == '__main__':
    warnings.filterwarnings("ignore")

    sys.excepthook = except_hook

    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    window = AppQT()
    sys.exit(app.exec_())

    #ar.update_ar_data()


