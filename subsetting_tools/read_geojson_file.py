#!/usr/bin/env python
u"""
read_geojson_file.py
Written by Tyler Sutterley (06/2019)
Reads polygons from GeoJSON files

INPUTS:
	input GeoJSON file (.json, .geojson)

OUTPUT:
	shapely multipolygon object of input file

PYTHON DEPENDENCIES:
	numpy: Scientific Computing Tools For Python
		http://www.numpy.org
		http://www.scipy.org/NumPy_for_Matlab_Users
	geojson: Functions for encoding and decoding GeoJSON formatted data
		https://pypi.org/project/geojson/
	shapely: PostGIS-ish operations outside a database context for Python
		http://toblerity.org/shapely/index.html

UPDATE HISTORY:
	Written 06/2019
"""
from __future__ import print_function

import os
import geojson
import numpy as np
from shapely.geometry import Polygon, MultiPolygon

#-- PURPOSE: read GeoJSON (.json, .geojson) files
def read_geojson_file(input_file):
	#-- read the GeoJSON file
	with open(os.path.expanduser(input_file),'r') as f:
		gj = geojson.load(f)

	#-- list of polygons
	poly_list = []
	#-- find features of interest
	f = [f for f in gj.features if f.geometry.type in ('LineString','Polygon')]
	#-- for each line string or polygon feature
	for feature in f:
		#-- extract coordinates for feature
		x,y = np.transpose(feature.geometry.coordinates)
		poly_obj = Polygon(list(zip(x,y)))
		#-- Valid Polygon cannot have overlapping exterior or interior rings
		if (not poly_obj.is_valid):
			poly_obj = poly_obj.buffer(0)
		poly_list.append(poly_obj)
	#-- create shapely multipolygon object
	mpoly_obj = MultiPolygon(poly_list)
	#-- return the polygon object
	return mpoly_obj
