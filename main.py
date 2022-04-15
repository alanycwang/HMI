from PyQt5.QtWidgets import *
import matplotlib.pyplot as plt
import movie, util, sys, pickle, time, warnings, math
from PyQt5.QtCore import Qt

class AppQT(QMainWindow):
    def __init__(self):
        super().__init__()

        maps = pickle.load(open("./data/maps.pkl", "rb"))
        maps = [util.Magnetogram(map) for map in maps]
        m = movie.MoviePlayerQT(maps)
        print("Finished loading maps")

        self.setWindowTitle("HMI")
        self.setFixedSize(m.sizeHint())
        self.setCentralWidget(m)
        self.show()

def except_hook(cls, exception, traceback):
    sys.__excepthook__(cls, exception, traceback)

if __name__ == '__main__':
    warnings.filterwarnings("ignore")

    # tstart = astropy.time.Time('2022-01-21T09:45:00', scale='utc', format='isot')
    # tend = tstart + 1 * u.day + 90 * u.minute
    # maps = util.get_maps(tstart, tend, interval=3 * u.hour, gen_magnetogram=False)
    #
    # pickle.dump(maps, open("./data/maps.pkl", "wb"))


    sys.excepthook = except_hook

    app = QApplication(sys.argv)

    window = AppQT()
    sys.exit(app.exec_())


    # import sunpy.data.sample
    # import sunpy.map
    # temp = sunpy.map.Map(sunpy.data.sample.AIA_171_IMAGE)
    # a = temp.date + 1*u.hour - temp.date
    # print(a)
    # print(type(a))

