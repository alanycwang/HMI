#for some reason, pip doesn't properly install all of sunpy's dependencies - this script is much easier to use anyways

import subprocess
import sys
import os

python_executable = "/Users/awang/Documents/pypy3.7-v7.3.9-osx64/bin/pypy"

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
        import reproject

        break

    except ModuleNotFoundError as e:
        m = str(e)[17:-1].replace('-', '_')
        print(m)
        if m == "skimage":
            subprocess.call([python_executable, "-m", "pip", "install", "--trusted-host", "pypi.org", "--trusted-host", "files.pythonhosted.org", "scikit-image", "-vvv"]) #skimage is called scikit-image apparently
        else: 
            subprocess.call([python_executable, "-m", "pip", "install", "--trusted-host", "pypi.org", "--trusted-host", "files.pythonhosted.org", m, "-vvv"])
            