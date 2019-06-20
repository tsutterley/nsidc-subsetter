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
	pyshp: Python read/write support for ESRI Shapefile format
		https://github.com/GeospatialPython/pyshp
	shapely: PostGIS-ish operations outside a database context for Python
		http://toblerity.org/shapely/index.html

UPDATE HISTORY:
	Written 06/2019
"""
from __future__ import print_function

import os
import re
import io
import zipfile
import shapefile
import numpy as np
from shapely.geometry import Polygon, MultiPolygon

#-- PURPOSE: read shapefiles
def read_shapefile(input_file, ZIP=False):
	#-- read input zipfile containing shapefiles
	if ZIP:
		#-- read the compressed shapefile and extract entities
		zs = zipfile.ZipFile(os.path.expanduser(input_file))
		dbf,prj,shp,shx = [io.BytesIO(zs.read(s)) for s in sorted(zs.namelist())
			if re.match('(.*?)\.(dbf|prj|shp|shx)$',s)]
		shape_input = shapefile.Reader(dbf=dbf, prj=prj, shp=shp, shx=shx,
			encodingErrors='ignore')
		#-- close the zipfile
		zs.close()
	else:
		#-- read the shapefile and extract entities
		shape_input = shapefile.Reader(os.path.expanduser(input_file))

	#-- extract attributes and entities
	shape_entities = shape_input.shapes()
	shape_attributes = shape_input.records()
	shape_field_names = [f[0] for f in shape_input.fields[1:]]

	#-- list of polygons
	poly_list = []
	#-- for each entity
	for i,ent in enumerate(shape_entities):
		#-- extract coordinates for entity
		points = np.array(ent.points)
		poly_obj = Polygon(list(zip(points[:,0], points[:,1])))
			#-- Valid Polygon cannot have overlapping exterior or interior rings
		if (not poly_obj.is_valid):
			poly_obj = poly_obj.buffer(0)
		poly_list.append(poly_obj)
	#-- create shapely multipolygon object
	mpoly_obj = MultiPolygon(poly_list)
	#-- return the polygon object
	return mpoly_obj
