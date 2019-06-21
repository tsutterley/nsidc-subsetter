#!/usr/bin/env python
u"""
read_shapefile.py
Written by Tyler Sutterley (06/2019)
Reads polygons from ESRI shapefiles

INPUTS:
	input shapefile (.shp)

OUTPUT:
	shapely multipolygon object of input file

OPTIONS:
	ZIP: input file is compressed

PYTHON DEPENDENCIES:
	numpy: Scientific Computing Tools For Python
		http://www.numpy.org
		http://www.scipy.org/NumPy_for_Matlab_Users
	fiona: Python wrapper for vector data access functions from the OGR library
		https://fiona.readthedocs.io/en/latest/manual.html
	shapely: PostGIS-ish operations outside a database context for Python
		http://toblerity.org/shapely/index.html

UPDATE HISTORY:
	Updated 06/2019: using fiona for consistency between read functions
	Written 06/2019
"""
from __future__ import print_function

import os
import fiona
import numpy as np
from shapely.geometry import Polygon, MultiPolygon

#-- PURPOSE: read shapefiles
def read_shapefile(input_file, ZIP=False):
	#-- read input zipfile containing shapefiles
	if ZIP:
		#-- read the compressed shapefile and extract entities
		shape = fiona.open('zip://{0}'.format(os.path.expanduser(input_file)))
	else:
		#-- read the shapefile and extract entities
		shape = fiona.open(os.path.expanduser(input_file))

	#-- list of polygons
	poly_list = []
	#-- for each entity
	for i,ent in enumerate(shape.values):
		#-- extract coordinates for entity
		points = np.squeeze(ent['geometry']['coordinates'])
		poly_obj = Polygon(list(zip(points[:,0], points[:,1])))
			#-- Valid Polygon cannot have overlapping exterior or interior rings
		if (not poly_obj.is_valid):
			poly_obj = poly_obj.buffer(0)
		poly_list.append(poly_obj)
	#-- create shapely multipolygon object
	mpoly_obj = MultiPolygon(poly_list)
	#-- return the polygon object
	return mpoly_obj
