#!/usr/bin/env python
u"""
polygon.py
Written by Tyler Sutterley (11/2021)
Reads polygons from GeoJSON, kml/kmz or ESRI shapefile files

INPUTS:
    input polygon file

OUTPUT:
    shapely multipolygon object of input file

OPTIONS:
    EPSG: projection identifier for output coordinates
    VARIABLES: reduce to a specific set of identifiers

PYTHON DEPENDENCIES:
    numpy: Scientific Computing Tools For Python
        https://numpy.org
        https://numpy.org/doc/stable/user/numpy-for-matlab-users.html
    fiona: Python wrapper for vector data access functions from the OGR library
        https://fiona.readthedocs.io/en/latest/manual.html
    geopandas: Python tools for geographic data
        http://geopandas.readthedocs.io/
    shapely: PostGIS-ish operations outside a database context for Python
        http://toblerity.org/shapely/index.html
    pyproj: Python interface to PROJ library
        https://pypi.org/project/pyproj/

UPDATE HISTORY:
    Updated 11/2021: add initial functions for clustering multipolygons
    Updated 08/2021: add functions for convex hull and exterior coordinates
    Written 10/2020
"""
from __future__ import print_function

import os
import io
import re
import copy
import fiona
import pyproj
import zipfile
import osgeo.gdal
import geopandas
import numpy as np
import sklearn.cluster
import shapely.geometry
# enable kml driver for geopandas
fiona.drvsupport.supported_drivers['LIBKML'] = 'rw'

class polygon(object):
    """
    Data class for reading polygon files
    """
    np.seterr(invalid='ignore')
    def __init__(self, epsg=4326):
        self.filename=None
        self.feature=None
        self.epsg=epsg
        self.shape=None

    def case_insensitive_filename(self,filename):
        """
        Searches a directory for a filename without case dependence
        """
        self.filename = os.path.expanduser(filename)
        #-- check if file presently exists with input case
        if not os.access(self.filename,os.F_OK):
            #-- search for filename without case dependence
            basename = os.path.basename(filename)
            directory = os.path.dirname(os.path.expanduser(filename))
            f = [f for f in os.listdir(directory) if re.match(basename,f,re.I)]
            if not f:
                raise IOError('{0} not found in file system'.format(filename))
            self.filename = os.path.join(directory,f.pop())
        return self

    def from_geojson(self, filename, variables=None):
        """
        read GeoJSON (.json, .geojson) files
        """
        # set filename
        self.case_insensitive_filename(filename)
        # read the GeoJSON file
        gj = geopandas.read_file(self.filename)

        #-- converting x,y from polygon projection to output EPSG
        crs1 = pyproj.CRS.from_string(gj.crs['init'])
        crs2 = pyproj.CRS.from_string("epsg:{0:d}".format(self.epsg))
        transformer = pyproj.Transformer.from_crs(crs1, crs2, always_xy=True)

        # list of polygons
        poly_list = []
        # find features of interest
        geometries = ('LineString','Polygon')
        f = [f for f in gj.iterfeatures() if f['geometry']['type'] in geometries]
        # reduce to variables of interest if specified
        f = [ft for ft in f if ft['id'] in variables] if variables else f

        # for each line string or polygon feature
        for feature in f:
            # extract coordinates for feature
            x,y = np.transpose(feature['geometry']['coordinates'])
            # convert points to EPSG
            xi,yi = transformer.transform(x, y)
            # create shapely polygon
            poly_obj = shapely.geometry.Polygon(np.c_[xi,yi])
            # cannot have overlapping exterior or interior rings
            if (not poly_obj.is_valid):
                poly_obj = poly_obj.buffer(0)
            poly_list.append(poly_obj)
        # create shapely multipolygon object
        # return the polygon object
        self.feature = shapely.geometry.MultiPolygon(poly_list)
        self.shape = (len(self.feature),)
        return self

    def from_kml(self, filename, kmz=False, variables=None):
        """
        read keyhole markup language (.kml) files
        """
        # set filename
        self.case_insensitive_filename(filename)
        # if input file is compressed
        if kmz:
            # decompress and parse KMZ file
            z = zipfile.ZipFile(self.filename, 'r')
            kml_file, = [s for s in z.namelist() if re.search(r'\.(kml)$',s)]
            # need to use osgeo virtual file system to add suffix to mmap name
            mmap_name = "/vsimem/{0}".format(kml_file)
            osgeo.gdal.FileFromMemBuffer(mmap_name, z.read(kml_file))
            with fiona.Collection(mmap_name, driver='LIBKML') as f:
                kml = geopandas.GeoDataFrame.from_features(f, crs=f.crs)
        else:
            kml = geopandas.read_file(self.filename)

        #-- converting x,y from polygon projection to output EPSG
        crs1 = pyproj.CRS.from_string(kml.crs['init'])
        crs2 = pyproj.CRS.from_string("epsg:{0:d}".format(self.epsg))
        transformer = pyproj.Transformer.from_crs(crs1, crs2, always_xy=True)

        # list of polygons
        poly_list = []

        # find features of interest
        geometries = ('LineString','Polygon')
        f = [f for f in kml.iterfeatures() if f['geometry']['type'] in geometries]
        # reduce to variables of interest if specified
        f = [ft for ft in f if ft['id'] in variables] if variables else f

        # for each line string or polygon feature
        for feature in f:
            # extract coordinates for feature
            coords = np.squeeze(feature['geometry']['coordinates'])
            # convert points to EPSG
            xi,yi = transformer.transform(coords[:,0], coords[:,1])
            # create polygon from coordinate set
            poly_obj = shapely.geometry.Polygon(np.c_[xi,yi])
            # cannot have overlapping exterior or interior rings
            if (not poly_obj.is_valid):
                poly_obj = poly_obj.buffer(0)
            poly_list.append(poly_obj)
        # create shapely multipolygon object
        # return the polygon object
        self.feature = shapely.geometry.MultiPolygon(poly_list)
        self.shape = (len(self.feature),)
        return self

    def from_shapefile(self, filename, zip=False, variables=None):
        """
        read ESRI shapefiles
        """
        # set filename
        self.case_insensitive_filename(filename)
        # read input zipfile containing shapefiles
        if zip:
            # read the compressed shapefile and extract entities
            shape = fiona.open('zip://{0}'.format(self.filename))
        else:
            # read the shapefile and extract entities
            shape = fiona.open(self.filename,'r')

        #-- converting x,y from polygon projection to output EPSG
        crs1 = pyproj.CRS.from_string(shape.crs['init'])
        crs2 = pyproj.CRS.from_string("epsg:{0:d}".format(self.epsg))
        transformer = pyproj.Transformer.from_crs(crs1, crs2, always_xy=True)

        # find features of interest
        geometries = ('LineString','Polygon')
        f = [f for f in shape.values() if f['geometry']['type'] in geometries]
        # reduce to variables of interest if specified
        f = [ft for ft in f if ft['id'] in variables] if variables else f

        # list of polygons
        poly_list = []
        # for each entity
        for i,ent in enumerate(f):
            # extract coordinates for entity
            for coords in ent['geometry']['coordinates']:
                # convert points to latitude/longitude
                x,y = np.transpose(coords)
                # convert points to EPSG
                xi,yi = transformer.transform(x, y)
                # create shapely polygon
                poly_obj = shapely.geometry.Polygon(np.c_[xi,yi])
                # cannot have overlapping exterior or interior rings
                if (not poly_obj.is_valid):
                    poly_obj = poly_obj.buffer(0)
                poly_list.append(poly_obj)
        # create shapely multipolygon object
        # return the polygon object
        self.feature = shapely.geometry.MultiPolygon(poly_list)
        self.shape = (len(self.feature),)
        return self

    def simplify(self, tolerance, preserve_topology=True):
        """
        Simplify representation of the geometric object
        """
        self.feature = self.feature.simplify(tolerance,
            preserve_topology=preserve_topology)
        self.shape = (len(self.feature),)
        return self

    def cluster(self, max_clusters=25):
        """
        Cluster polygons using k-means clustering
        """
        # subdivide regions using k-means clustering
        centroids = np.squeeze([g.centroid.xy for g in self.feature])
        nmax = len(centroids)
        # k-means within-cluster sum of squares
        wcss = np.zeros((max_clusters-1))
        AIC = np.zeros((max_clusters-1))
        # for each test number of clusters
        for i in range(1, max_clusters):
            kmeans = sklearn.cluster.KMeans(n_clusters=i,
                init = 'k-means++', random_state=42)
            kmeans.fit(centroids)
            # within-cluster sum of squares
            wcss[i-1] = kmeans.inertia_
            # estimate AIC criterion
            log_lik = 0.5*(-nmax*(np.log(2.0 * np.pi) + 1.0 -
                np.log(nmax) + np.log(wcss[i-1])))
            AIC[i-1] = -2.0*log_lik + 2.0*np.float64(i + 1)
        #-- maximum number of clusters based on elbow method
        n_clusters = np.max(np.nonzero(AIC[1:] < AIC[0:-1]))
        kmeans = sklearn.cluster.KMeans(n_clusters=n_clusters,
            init='k-means++', random_state=5,  max_iter=400)
        # cluster for each centroid
        k = kmeans.fit_predict(centroids)
        # output polygon object
        temp = polygon(epsg=self.epsg)
        temp.feature = []
        temp.shape = (n_clusters,)
        for cluster in range(n_clusters):
            mp = shapely.geometry.MultiPolygon(self.feature[k == cluster])
            temp.feature[cluster] = mp.convex_hull
        # return cluster
        return temp

    def chunk(self, max_features=500, max_vertices=5000):
        """
        Reduce geometric object to lists with
            number of features and vertices
        """
        offset = 0
        features = [[]]*(self.shape[0]//max_features)
        for tol in range(0.0,1.0,0.1):
            s = self.feature.simplify(tol)
            n_vertices = np.max([len(p.exterior.coords) for p in s])
            if (n_vertices < max_vertices):
                break

    def bounds(self):
        """
        Return the bounding box of the geometric object
        """
        return self.feature.bounds

    def convex_hull(self):
        """
        Calculate the convex hull of the geometric object
        """
        self.feature = shapely.geometry.polygon.orient(
            self.feature.convex_hull,sign=1)
        self.shape = np.shape(self.feature)
        return self

    def xy(self):
        """
        Return the coordinates of the geometric object
        """
        return self.feature.exterior.xy
