from astropy.coordinates import SkyCoord
import astropy.units as u
import numpy as np
import sunpy.map

# used alongside Movie class to determine movie properties (should be inherited from by other classes)
# This makes it easier to implement differences in movie player functions across different types of images
# It's also easier to modify the movie player itself, as all functions that are part of the movie player will therefore be generalized to any type of projection or image
class Projection_():
    unit = None #map units - usually either degrees or arcseconds
    u = None #unit but in astropy.units
    code = None #three letter "code" for this type of projection - used by mlist class to identify projection
    cname = None #full name of coordinate system
    ratio = None #w/h ratio of data
    xrange = (None, None) #range of x coordinates
    yrange = (None, None) #range of y coordinates

    def __str__(self):
        return self.code

    def get_lat_lon(self, coord:SkyCoord): # get proper coordinates from SkyCoord Object
        return None

    def get_scale(self, sl): #get optimized scale depending on width cutout
        return 4096

    def transform(self, data): #applies rotations, flips, etc to display image correctly on pyqtgraph
        return data

    def transform_coord(self, coords, scale=None): #transforms from original coordinate system to one compatible with pyqtgraph
        return coords

    def inverse_transform(self, coords, scale=None):
        return coords

    def from_hpc(self, _): #converts to this projection from hpc
        raise TransformError("Projection is a base class and does not represent a specific map projection.")

    def get_scale(self, _):  #determine scale of new image based off the window size of cutout
        return None

    def get_scales(self): #returns the scales that should be kept for zooming in - MUST ALWAYS BE IN INCREASING ORDER
        return 1024, 2048, 4096

class HelioprojectiveCartesian_(Projection_):
    unit = "arcsec"
    u = u.arcsec
    code = "hpc"
    cname = "Helioprojective"
    ratio = 1
    xrange = (-1024, 1024)
    yrange = (-1024, 1024)

    def get_lat_lon(self, coord:SkyCoord):
        return coord.Tx.arcsec, coord.Ty.arcsec

    def transform(self, data):
        return np.flip(np.rot90(data), axis=1)/((4096/len(data))**2)
    
    def transform_coord(self, coords, scale=None):
        if scale is None:
            raise TransformError("Must provide scale for HPC transformation")
        x, y = coords
        return (scale - y, scale - x)

    def inverse_transform(self, coords, scale=None):
        if scale is None:
            raise TransformError("Must provide scale for HPC transformation")
        x, y = coords
        return (scale - y, scale - x)

    def from_hpc(self, map):
        return map

    def get_scale(self, sl):
        if sl < 2048:
            scale = 4096
        elif sl < 3072:
            scale = 2048
        else:
            scale = 1024
        return scale 

class Heliographic_(Projection_): #base class for all heliographic coordinate systems
    unit = "degree"
    u = u.degree
    code = None
    cname = "Heliographic"
    xrange = (-180, 180)
    yrange = (-90, 90)

    def get_lat_lon(self, coord:SkyCoord):
        return coord.lon.degree, coord.lat.degree

    def get_scale(self, sl):
        if sl < 1536:
            scale = 2048
        else:
            scale = 1024
        return scale

    def get_scales(self): 
        return 1024, 2048

class CylindricalEqualArea_(Heliographic_):
    code = "cea"
    ratio = np.pi

    def transform(self, data):
        return np.flip(np.rot90(data), axis=0)/((2048/len(data)))

    def transform_coord(self, coords, scale=None): #transforms from original coordinate system to one compatible with pyqtgraph
        x, y = coords
        return y, x

    def inverse_transform(self, coords, scale=None):
        return self.transform_coord(coords)
    
    #reprojects a sunpy map to Lambert CEA
    #m must be a sunpy map - a reprojection of this map will be returned
    #coord is a SkyCoord object that determines the centering of the outputted reprojection. If given, the image will be rotated so that coord will be at the center. This results in less distortion at coord
    #alternatively, the user can give origin_x and origin_y for the same effect. If origin_x and origin_y are not heliographic stonyhurst, frame can be set to the frame of these coordinates
    #if clip=True, the image will be clipped so that both dimensions are a multiple of 4. This allows easier downscaling without interpolation
    #instead of providing a specific dimension for the projection, the user can also provide a float, determining the scale in degrees per pixel of the image
    def from_hpc(self, m, coord=None, h=4096, origin_x=0, origin_y=0, clip=True, frame="heliographic_stonyhurst", scale=None, algorithm='interpolation'):
        if scale is not None:
            w = int(360/scale + 0.5)
            h = w/np.pi
        else:
            w = h*np.pi
            scale = 360/(w)
        if coord is None:
            frame_out = SkyCoord(origin_x, origin_y, unit=u.deg, frame=frame, obstime=m.date, rsun=m.coordinate_frame.rsun)
        else:
            frame_out = coord
        if clip:
            w = int(w + 2 - (w + 2)%4) #make sure it's divisible by 4 for easier downscaling
            h = int(h + 2 - (h + 2)%4)
        else:
            w = int(w + 0.5)
        header = sunpy.map.make_fitswcs_header((h, w), frame_out, scale=(scale, scale)*u.deg/u.pix, projection_code="CEA") #since the deg/pix ratio for lattitude is not linear, giving the correct ratio makes the projection overcompensate for nonlinearity
        return m.reproject_to(header, algorithm=algorithm)

#an instance of each usable Projection class should be created here
CylindricalEqualArea = CylindricalEqualArea_()
HelioprojectiveCartesian = HelioprojectiveCartesian_()

class TransformError(Exception):
    pass