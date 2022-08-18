#for some reason, pip doesn't properly install all of sunpy's dependencies - this script is much easier to use anyways

import subprocess
import sys
import os

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
        import superqt
        from sunpy import timeseries as ts
        import shutil
        from contextlib import closing
        import paramiko
        import pyqtgraph
        import mpl_animators

        break

    except ModuleNotFoundError as e:
        m = str(e)[17:-1].replace('-', '_')
        if m == "skimage":
            subprocess.call(["python3", "-m", "pip", "install", "--trusted-host", "pypi.org", "--trusted-host", "files.pythonhosted.org", "scikit-image", "-vvv"]) #skimage is called scikit-image apparently
        else: 
            subprocess.call(["python3", "-m", "pip", "install", "--trusted-host", "pypi.org", "--trusted-host", "files.pythonhosted.org", m, "-vvv"])
            