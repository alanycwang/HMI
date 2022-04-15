import matplotlib.pyplot as plt
import sunpy.map

if __name__ == '__main__':
    syn_map = sunpy.map.Map('http://jsoc.stanford.edu/data/hmi/synoptic/hmi.Synoptic_Mr.2191.fits')

    fig = plt.figure(figsize=(12, 5))
    ax = plt.subplot(projection=syn_map)
    im = syn_map.plot(ax)
    plt.show()