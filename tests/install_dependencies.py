#for some reason, pip doesn't properly install all of sunpy's dependencies - this script is much easier to use anyways

import subprocess
import sys

while True:
    try:
        #add other packages as needed
        import matplotlib.pyplot as plt
        import sunpy.map
        from sunpy.net import Fido
        from sunpy.net import attrs as a
        import drms
        import astropy.time
        import astropy.units as u
        import urllib.request, urllib.error
        import tkinter as tk
        import skimage
        import reproject
        import PyQt5

        break

    except ModuleNotFoundError as e:
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", str(e)[17:-1]])

        except subprocess.CalledProcessError:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "scikit-image"]) #skimage is called scikit-image apparently