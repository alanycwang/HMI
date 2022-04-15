import time
import _thread
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import tkinter as tk
from tkinter import ttk
from movie import MovieBase

class MovieTk(tk.Frame): #play movie of given sunpy maps

    speed = 0.5 #a frame every half second, can be modified while still playing
    images = []
    run = False
    stopped = False
    waiting = False

    def __init__(self, maps, **kwargs):
        super().__init__(**kwargs)
        self.maps=maps

    def start(self):
        try: self.pack_info()
        except tk.TclError:
            return

        self.run = True
        self.stopped = False

        self.controlframe = tk.Frame(self)
        self.controlframe.pack(side='bottom', expand=True)
        self.playbutton = ttk.Button(self.controlframe, text=u'\u23f8', command=self.pause, takefocus=False)
        self.playbutton.pack(side='left')
        self.progressbar = ttk.Scale(self.controlframe, length=500, from_=0, to=len(self.maps), orient=tk.HORIZONTAL, command=self.scroll, takefocus=False)
        self.progressbar.pack(side='left', expand=True)

        # pre-load all images to reduce flickering
        for map in self.maps:
            fig = plt.figure()
            ax = plt.subplot(projection=map)
            map.plot(ax)
            im = FigureCanvasTkAgg(fig, master=self)
            im.draw()
            self.images.append(im.get_tk_widget())

        for image in self.images:
            image.pack(side='top')
            self.update_idletasks()
            time.sleep(0.1)
            image.pack_forget()

        _thread.start_new_thread(self.cycle, ())

    def scroll(self, _):
        self.pause()
        while not self.waiting: #wait for cycle to finish whatever its doing
            pass
        self.images[self.i].pack_forget()
        self.i = int(self.progressbar.get())
        print(self.i)
        self.images[self.i].pack()

    def stop(self):
        self.run = False

    def pause(self):
        if self.stopped: return
        self.stopped = True
        self.playbutton.config(text=u'\u23f5', command=self.play)
        self.update_idletasks()

    def play(self):
        self.stopped = False
        self.playbutton.config(text=u'\u23f8', command=self.pause)
        self.update_idletasks()

    def cycle(self, start=0):
        self.i = start
        while self.run:
            self.progressbar.config(value=self.i)
            self.images[self.i].pack()
            time.sleep(self.speed)
            while self.stopped:
                self.waiting = True
                pass
            self.waiting = False
            self.images[self.i].pack_forget()
            self.i += 1
            self.i = self.i%len(self.images)

class MovieTK(FigureCanvasTkAgg, MovieBase):
    def __init__(self, maps, master):
        MovieBase.__init__(self, maps)
        FigureCanvasTkAgg.__init__(self, self.thumbnail(maps[0]), master=master)
        self.mpl_connect('button_press_event', self.click)

    def pack(self, *args, **kwargs):
        self.get_tk_widget().pack(*args, **kwargs)

    def grid(self, *args, **kwargs):
        self.get_tk_widget().grid(*args, **kwargs)