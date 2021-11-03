#!/usr/bin/env python
u"""
nsidc_subset_altimetry.py
Written by Tyler Sutterley (11/2021)

Program to acquire subset altimetry datafiles from the NSIDC API:
https://wiki.earthdata.nasa.gov/display/EL/How+To+Access+Data+With+Python
https://nsidc.org/support/faq/what-options-are-available-bulk-downloading-data-
    https-earthdata-login-enabled
https://nsidc.org/support/how/2018-agu-tutorial
https://cmr.earthdata.nasa.gov/search/site/docs/search/api.html
http://www.voidspace.org.uk/python/articles/authentication.shtml#base64

Register with NASA Earthdata Login system:
https://urs.earthdata.nasa.gov

Add NSIDC_DATAPOOL_OPS to NASA Earthdata Applications
https://urs.earthdata.nasa.gov/oauth/authorize?client_id=_JLuwMHxb2xX6NwYTb4dRA

CALLING SEQUENCE:
    python nsidc_subset_altimetry.py -T 2018-11-23T00:00:00 2018-11-23T23:59:59
        -B -50.33333 68.56667 -49.33333 69.56667 --version 004
        --user <username> -V ATL03
    where <username> is your NASA Earthdata username

INPUTS:
    GLAH12: GLAS/ICESat L2 Antarctic and Greenland Ice Sheet Altimetry Data
    ILATM2: Airborne Topographic Mapper Icessn Elevation, Slope, and Roughness
    ILATM1B: Airborne Topographic Mapper QFIT Elevation
    ILVIS1B: Land, Vegetation and Ice Sensor Geolocated Return Energy Waveforms
    ILVIS2: Geolocated Land, Vegetation and Ice Sensor Surface Elevation Product
    ATL03: Global Geolocated Photon Data
    ATL04: Normalized Relative Backscatter
    ATL06: Land Ice Height
    ATL07: Sea Ice Height
    ATL08: Land and Vegetation Height
    ATL09: Atmospheric Layer Characteristics
    ATL10: Sea Ice Freeboard
    ATL12: Ocean Surface Height
    ATL13: Inland Water Surface Height

COMMAND LINE OPTIONS:
    --help: list the command line options
    -D X, --directory X: working data directory
    -U X, --user X: username for NASA Earthdata Login
    -P X, --password X: password for NASA Earthdata Login
    -N X, --netrc X: path to .netrc file for alternative authentication
    --version: version of the dataset to use
    -B X, --bbox X: Bounding box (lonmin,latmin,lonmax,latmax)
    -P X, --polygon X: Georeferenced file containing a set of polygons
    -T X, --time X: Time range (comma-separated start and end)
    -F X, --format X: Output data format (TABULAR_ASCII, NetCDF4)
    -L, --list: Create an index file of CMR query granules
    -M X, --mode X: Local permissions mode of the files processed
    -V, --verbose: Verbose output of processing
    -Z, --unzip: Unzip dataset from NSIDC subsetting service

PYTHON DEPENDENCIES:
    fiona: Python wrapper for vector data access functions from the OGR library
        https://fiona.readthedocs.io/en/latest/manual.html
    geopandas: Python tools for geographic data
        http://geopandas.readthedocs.io/
    shapely: PostGIS-ish operations outside a database context for Python
        http://toblerity.org/shapely/index.html
    scikit-learn: Machine Learning in Python
        http://scikit-learn.org/stable/index.html
        https://github.com/scikit-learn/scikit-learn

PROGRAM DEPENDENCIES:
    polygon.py: Reads polygons from GeoJSON, kml/kmz or ESRI shapefile files
    utilities.py: Download and management utilities for syncing files

UPDATE HISTORY:
    Updated 11/2021: use scrolling CMR queries to get the number of pages
    Updated 04/2021: set a default netrc file and check access
        default credentials from environmental variables
    Updated 10/2020: using argparse to set parameters from the command line
        use utilities to build https opener for CMR requests and NSIDC download
        use combined polygon module to read georeferenced files
    Updated 05/2020: added option netrc to use alternative authentication
    Updated 03/2020: simplify polygon extension if statements
        raise exception if polygon file extension is not presently available
    Updated 09/2019: added ssl context to urlopen headers
    Updated 07/2019: can use specific identifiers within a georeferenced file
    Updated 06/2019: added option polygon to subset using a georeferenced file
        added read functions for kml/kmz georeferenced files
    Written 01/2019
"""
from __future__ import print_function

import sys
import os
import io
import re
import json
import math
import time
import netrc
import shutil
import getpass
import logging
import zipfile
import builtins
import argparse
import posixpath
import dateutil.parser
import subsetting_tools.polygon
import subsetting_tools.utilities

#-- PURPOSE: build string for version queries
def build_version_query(version, desired_pad_length=3):
    #-- check that the version is less than the required
    if (len(str(version)) > desired_pad_length):
        raise Exception('Version string too long: "{0}"'.format(version))
    #-- Strip off any leading zeros
    version = int(version)
    query_params = ""
    while (len(str(version)) <= desired_pad_length):
        padded_version = str(version).zfill(desired_pad_length)
        query_params += '&version={0}'.format(padded_version)
        desired_pad_length -= 1
    #-- return the query parameters
    return query_params

#-- PURPOSE: Select only the desired data files from CMR response
def cmr_filter_json(search_page, form="application/x-hdfeos"):
    #-- check that there are urls for request
    urls = list()
    if (('feed' not in search_page.keys()) or
        ('entry' not in search_page['feed'].keys())):
        return urls
    #-- iterate over references and get cmr location
    for entry in search_page['feed']['entry']:
        #-- find url for format type
        for i,link in enumerate(entry['links']):
            if ('type' in link.keys()) and (link['type'] == form):
                urls.append(entry['links'][i]['href'])
    return urls

#-- PURPOSE: program to acquire subsetted NSIDC data
def nsidc_subset_altimetry(filepath, PRODUCT, VERSION, BBOX=None, POLYGON=None,
    TIME=None, FORMAT=None, VERBOSE=False, LIST=False, UNZIP=False, MODE=None):

    #-- create logger
    loglevel = logging.INFO if VERBOSE else logging.CRITICAL
    logging.basicConfig(level=loglevel)

    #-- product and version flags
    product_flag = '?short_name={0}'.format(PRODUCT)
    version_flag = build_version_query(VERSION) if VERSION else ''
    #-- if changing the output format
    format_flag = '&format={0}'.format(FORMAT) if FORMAT else ''

    #-- if using time start and end to temporally subset data
    if TIME:
        #-- verify that start and end times are in ISO format
        start_time = dateutil.parser.parse(TIME[0]).isoformat()
        end_time = dateutil.parser.parse(TIME[1]).isoformat()
        time_flag = '&time={0},{1}'.format(start_time, end_time)
        temporal_flag = '&temporal={0},{1}'.format(start_time, end_time)
    else:
        time_flag = ''
        temporal_flag = ''

    #-- spatially subset data using bounding box or polygon file
    if BBOX:
        #-- if using a bounding box to spatially subset data
        #-- API expects: min_lon,min_lat,max_lon,max_lat
        bounds_flag = '&bounding_box={0:f},{1:f},{2:f},{3:f}'.format(*BBOX)
        spatial_flag = '&bbox={0:f},{1:f},{2:f},{3:f}'.format(*BBOX)
    elif POLYGON:
        #-- read shapefile or kml/kmz file
        _,fileExtension = os.path.splitext(POLYGON)
        #-- extract file name and subsetter indices lists
        match_object = re.match(r'(.*?)(\[(.*?)\])?$',POLYGON)
        f = os.path.expanduser(match_object.group(1))
        #-- read specific variables of interest
        v = match_object.group(3).split(',') if match_object.group(2) else None
        #-- get MultiPolygon object from input spatial file
        if fileExtension in ('.shp','.zip'):
            #-- if reading a shapefile or a zipped directory with a shapefile
            ZIP = (fileExtension == '.zip')
            mpoly=subsetting_tools.polygon().from_shapefile(f,variables=v,zip=ZIP)
        elif fileExtension in ('.kml','.kmz'):
            #-- if reading a keyhole markup language (can be compressed kmz)
            KMZ = (fileExtension == '.kmz')
            mpoly=subsetting_tools.polygon().from_kml(f,variables=v,kmz=KMZ)
        elif fileExtension in ('.json','.geojson'):
            #-- if reading a GeoJSON file
            mpoly=subsetting_tools.polygon().from_geojson(f,variables=v)
        else:
            raise IOError('Unlisted polygon type ({0})'.format(fileExtension))
        #-- calculate the bounds of the MultiPolygon object
        BBOX = mpoly.bounds()
        bounds_flag = '&bounding_box={0:f},{1:f},{2:f},{3:f}'.format(*BBOX)
        #-- calculate the convex hull of the MultiPolygon object for subsetting
        #-- the CMR api requires polygons to be in counter-clockwise order
        qhull = mpoly.convex_hull()
        #-- get exterior coordinates of complex hull
        X,Y = qhull.xy()
        #-- coordinate order for polygon flag is lon1,lat1,lon2,lat2,...
        polygon_flag = ','.join(['{0:f},{1:f}'.format(x,y) for x,y in zip(X,Y)])
        spatial_flag = '&polygon={0}'.format(polygon_flag)
    else:
        #-- do not spatially subset data
        bounds_flag = ''
        spatial_flag = ''

    #-- get dictionary of granules for temporal and spatial subset
    HOST=posixpath.join('https://cmr.earthdata.nasa.gov','search','granules.json')
    page_size = 100
    request_mode = 'stream'
    granules = []
    cmr_scroll_id = None
    while True:
        #-- flags for page size
        size_flag = '&page_size={0:d}'.format(page_size)
        #-- url for page
        cmr_query_url = ''.join([HOST,product_flag,'&provider=NSIDC_ECS',
            '&sort_key[]=start_date','&sort_key[]=producer_granule_id',
            '&scroll=true',version_flag,bounds_flag,
            temporal_flag,size_flag])
        request = subsetting_tools.utilities.urllib2.Request(cmr_query_url)
        if cmr_scroll_id:
            request.add_header('cmr-scroll-id', cmr_scroll_id)
        response=subsetting_tools.utilities.urllib2.urlopen(request, timeout=20)
        if not cmr_scroll_id:
            # Python 2 and 3 have different case for the http headers
            headers = {k.lower(): v for k, v in dict(response.info()).items()}
            cmr_scroll_id = headers['cmr-scroll-id']
            hits = int(headers['cmr-hits'])
        #-- parse the json response
        search_page = json.loads(response.read())
        url_scroll_results = cmr_filter_json(search_page)
        if not url_scroll_results:
            break
        granules.extend(url_scroll_results)

    #-- if creating a list of CMR query granules
    if LIST:
        fid = open(filepath,'index.txt','w')
        for granule in granules:
            print(posixpath.basename(granule),file=fid)
        fid.close()

    #-- number of orders needed for requests
    page_num = math.ceil(len(granules)/page_size)

    #-- for each page of data
    for p in range(1,page_num):
        #-- flags for page size and page number
        size_flag = '&page_size={0:d}'.format(page_size)
        num_flag = '&page_num={0:d}'.format(p)
        request_flag = '&request_mode={0}'.format(request_mode)
        #-- remote https server for page of NSIDC Data
        HOST = posixpath.join('https://n5eil02u.ecs.nsidc.org','egi','request')
        remote_url = ''.join([HOST,product_flag,version_flag,bounds_flag,
            spatial_flag,time_flag,format_flag,size_flag,num_flag,request_flag])

        #-- local file
        today = time.strftime('%Y-%m-%dT%H-%M-%S',time.localtime())
        #-- download as either zipped file (default) or unzip to a directory
        if UNZIP:
            #-- Create and submit request. There are a wide range of exceptions
            #-- that can be thrown here, including HTTPError and URLError.
            request = subsetting_tools.utilities.urllib2.Request(remote_url)
            response = subsetting_tools.utilities.urllib2.urlopen(request)
            #-- read to BytesIO object
            fid = io.BytesIO(response.read())
            #-- use zipfile to extract contents from bytes
            remote_data = zipfile.ZipFile(fid)
            subdir = '{0}_{1}'.format(PRODUCT,today)
            logging.info('{0} -->\n'.format(remote_url))
            #-- extract each member and convert permissions to MODE
            for member in remote_data.filelist:
                member.filename = os.path.basename(member.filename)
                local_file = os.path.join(filepath,subdir,member.filename)
                logging.info('\t{0}\n'.format(local_file))
                remote_data.extract(member, path=os.path.join(filepath,subdir))
                os.chmod(local_file, MODE)
            #-- close the zipfile object
            remote_data.close()
        else:
            #-- Printing files transferred
            local_zip=os.path.join(filepath,'{0}_{1}.zip'.format(PRODUCT,today))
            args = (remote_url,local_zip)
            logging.info('{0} -->\n\t{1}\n'.format(*args))
            #-- Create and submit request. There are a wide range of exceptions
            #-- that can be thrown here, including HTTPError and URLError.
            request = subsetting_tools.utilities.urllib2.Request(remote_url)
            response = subsetting_tools.utilities.urllib2.urlopen(request)
            #-- copy contents to local file using chunked transfer encoding
            #-- transfer should work properly with ascii and binary data formats
            CHUNK = 16 * 1024
            with open(local_zip, 'wb') as f:
                shutil.copyfileobj(response, f, CHUNK)
            #-- keep remote modification time of file and local access time
            # os.utime(local_zip, (os.stat(local_zip).st_atime, remote_mtime))
            #-- convert permissions to MODE
            os.chmod(local_zip, MODE)

#-- Main program that calls nsidc_subset_altimetry()
def main(argv):

    #-- account for a bug in argparse that misinterprets negative arguments
    #-- preserves backwards compatibility of argparse for prior python versions
    for i, arg in enumerate(argv):
        if (arg[0] == '-') and arg[1].isdigit(): argv[i] = ' ' + arg

    #-- Products for the NSIDC subsetter
    P = {}
    #-- ICESat/GLAS
    P['GLAH12'] = 'GLAS/ICESat L2 Antarctic and Greenland Ice Sheet Altimetry'
    #-- Operation IceBridge
    P['ILATM2'] = 'Icebridge Airborne Topographic Mapper Icessn Product'
    P['ILATM1B'] = 'Icebridge Airborne Topographic Mapper QFIT Elevation'
    P['ILVIS1B'] = 'Icebridge LVIS Geolocated Return Energy Waveforms'
    P['ILVIS2'] = 'Icebridge Land, Vegetation and Ice Sensor Elevation Product'
    #-- ICESat-2/ATLAS
    P['ATL03'] = 'Global Geolocated Photon Data'
    P['ATL04'] = 'Normalized Relative Backscatter'
    P['ATL06'] = 'Land Ice Height'
    P['ATL07'] = 'Sea Ice Height'
    P['ATL08'] = 'Land and Vegetation Height'
    P['ATL09'] = 'Atmospheric Layer Characteristics'
    P['ATL10'] = 'Sea Ice Freeboard'
    P['ATL12'] = 'Ocean Surface Height'
    P['ATL13'] = 'Inland Water Surface Height'
    #-- Read the system arguments listed after the program
    parser = argparse.ArgumentParser()
    parser.add_argument('product',
        metavar='PRODUCT', type=str, nargs='+', choices=P.keys(),
        help='Altimetry Product')
    parser.add_argument('--directory','-D',
        type=lambda p: os.path.abspath(os.path.expanduser(p)),
        default=os.getcwd(),
        help='Working data directory')
    parser.add_argument('--user','-U',
        type=str, default=os.environ.get('EARTHDATA_USERNAME'),
        help='Username for NASA Earthdata Login')
    parser.add_argument('--password','-P',
        type=str, default=os.environ.get('EARTHDATA_PASSWORD'),
        help='Password for NASA Earthdata Login')
    parser.add_argument('--netrc','-N',
        type=lambda p: os.path.abspath(os.path.expanduser(p)),
        default=os.path.join(os.path.expanduser('~'),'.netrc'),
        help='Path to .netrc file for authentication')
    parser.add_argument('--version','-v',
        type=str,
        help='Version of the dataset to use')
    parser.add_argument('--bbox','-B',
        type=float, nargs=4, metavar=('lon_min','lat_min','lon_max','lat_max'),
        help='Bounding box')
    parser.add_argument('--polygon','-p',
        type=os.path.expanduser,
        help='Georeferenced file containing a set of polygons')
    parser.add_argument('--time','-T',
        type=str, nargs=2, metavar=('start_time','end_time'),
        help='Time range')
    parser.add_argument('--format','-F',
        type=str, choices=('TABULAR_ASCII','NetCDF4'),
        help='Convert to output data format')
    parser.add_argument('--list','-L',
        default=False, action='store_true',
        help='Create an index file of CMR query granules')
    parser.add_argument('--unzip','-Z',
        default=False, action='store_true',
        help='Unzip dataset from NSIDC subsetting service')
    parser.add_argument('--verbose','-V',
        default=False, action='store_true',
        help='Verbose output of run')
    parser.add_argument('--mode','-M',
        type=lambda x: int(x,base=8), default=0o775,
        help='Permissions mode of output files')
    args = parser.parse_args()

    #-- NASA Earthdata hostname
    URS = 'urs.earthdata.nasa.gov'
    #-- get authentication
    if not args.user and not os.access(args.netrc,os.F_OK):
        #-- check that NASA Earthdata credentials were entered
        args.user=builtins.input('Username for {0}: '.format(URS))
        #-- enter password securely from command-line
        args.password=getpass.getpass('Password for {0}@{1}: '.format(args.user,URS))
    elif not args.user and os.access(args.netrc,os.F_OK):
        args.user,_,args.password=netrc.netrc(args.netrc).authenticators(URS)
    else:
        #-- enter password securely from command-line
        args.password=getpass.getpass('Password for {0}@{1}: '.format(args.user,URS))
    #-- build an opener for NSIDC
    subsetting_tools.utilities.build_opener(args.user, args.password,
        authorization_header=False)

    #-- recursively create directory if presently non-existent
    if not os.access(args.directory, os.F_OK):
        os.makedirs(args.directory, args.mode)

    #-- check internet connection before attempting to run program
    HOST = 'https://n5eil01u.ecs.nsidc.org/'
    if subsetting_tools.utilities.check_connection(HOST):
        #-- for each altimetry product
        for p in args.product:
            #-- run program for product
            nsidc_subset_altimetry(args.directory, p, args.version,
                BBOX=args.bbox, POLYGON=args.polygon, TIME=args.time,
                FORMAT=args.format, LIST=args.list, UNZIP=args.unzip,
                VERBOSE=args.verbose, MODE=args.mode)

#-- run main program
if __name__ == '__main__':
    main(sys.argv)
