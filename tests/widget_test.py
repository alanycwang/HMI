import astropy.time
import astropy.units as u

import tkinter as tk
import movie, util


def movie():
    tstart = astropy.time.Time('2022-01-21T09:45:00', scale='utc', format='isot')
    tend = tstart + 1 * u.day + 90 * u.minute

    maps = movie.get_maps(tstart, tend=tend, interval=3 * u.hour)

    m = movie.Movie(maps)
    m.pack(padx=10, pady=10)
    m.start()


def search():
    s = movie.Search()
    s.pack(side="top", expand=True)


app = tk.Tk()
movie()
app.mainloop()
