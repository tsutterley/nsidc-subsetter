nsidc-subsetter
===============

[![Language](https://img.shields.io/badge/python-v3.7-green.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](https://github.com/tsutterley/nsidc-subsetter/blob/master/LICENSE)

#### Program for using the NSIDC subsetter api for retrieving NASA Operation IceBridge, ICESat and ICESat-2 data

- [NASA Earthdata Login system](https://urs.earthdata.nasa.gov)  
- [How to Access Data with Python](https://wiki.earthdata.nasa.gov/display/EL/How+To+Access+Data+With+Python)  
- [NSIDC: what download options are available](https://nsidc.org/support/faq/what-options-are-available-bulk-downloading-data-https-earthdata-login-enabled)  
- [NASA Earthdata CMR API Documentation](https://cmr.earthdata.nasa.gov/search/site/docs/search/api.html)  

Register with NASA Earthdata Login system and add **NSIDC_DATAPOOL_OPS** to your NASA Earthdata Applications

### Calling Sequence
```bash
python nsidc_subset_altimetry.py -T 2009-01-01T00:00:00,2009-12-31T23:59:59 \
	-B -50.33333,68.56667,-49.33333,69.56667 --version=034 -F NetCDF4 \
	--user=<username> -V -Z GLAH12
```

#### Products
- GLAH12: GLAS/ICESat L2 Antarctic and Greenland Ice Sheet Altimetry Data  
- ILATM2: Airborne Topographic Mapper Icessn Elevation, Slope, and Roughness  
- ILATM1B: Airborne Topographic Mapper QFIT Elevation  
- ILVIS1B: Land, Vegetation and Ice Sensor Geolocated Return Energy Waveforms  
- ILVIS2: Geolocated Land, Vegetation and Ice Sensor Surface Elevation Product  
- ATL03: Global Geolocated Photon Data  
- ATL04: Normalized Relative Backscatter  
- ATL06: Land Ice Height  
- ATL07: Sea Ice Height  
- ATL08: Land and Vegetation Height  
- ATL09: Atmospheric Layer Characteristics  
- ATL10: Sea Ice Freeboard  
- ATL12: Ocean Surface Height  
- ATL13: Inland Water Surface Height  

#### Options
	--help: list the command line options  
	-D X, --directory=X: working data directory  
	-U X, --user=X: username for NASA Earthdata Login  
    -N X, --netrc=X: Path to .netrc file for authentication  
	--version: version of the dataset to use  
	-B X, --bbox=X: Bounding box (lonmin,latmin,lonmax,latmax)  
	-P X, --polygon=X: Georeferenced file containing a set of polygons   
	-T X, --time=X: Time range (comma-separated start and end)  
	-F X, --format=X: Output data format (TABULAR_ASCII, NetCDF4)  
	-M X, --mode=X: Local permissions mode of the files processed  
	-V, --verbose: Verbose output of processing  
	-Z, --unzip: Unzip dataset from NSIDC subsetting service  

#### Georeferenced File Readers  
Can include a georeferenced file using the `--polygon` option.  
Presently subsets to the convex hull of the internal polygons.  
 - `read_geojson_file.py`: Reads polygons from GeoJSON files  
 - `read_kml_file.py`: Reads polygons from keyhole markup language (.kml or .kmz) files  
 - `read_shapefile.py`: Reads polygons from ESRI shapefiles (can be zipped)  

#### Dependencies
- [numpy: Scientific Computing Tools For Python](http://www.numpy.org)  
- [gdal: Pythonic interface to the Geospatial Data Abstraction Library (GDAL)](https://pypi.python.org/pypi/GDAL)  
- [shapely: PostGIS-ish operations outside a database context for Python](http://toblerity.org/shapely/index.html)  
- [fiona: Python wrapper for vector data access functions from the OGR library](https://fiona.readthedocs.io/en/latest/manual.html)  
- [geopandas: Python tools for geographic data](http://geopandas.readthedocs.io/)  
- [pyproj: Python interface to PROJ library](https://pypi.org/project/pyproj/)  
- [lxml: processing XML and HTML in Python](https://pypi.python.org/pypi/lxml)  
- [future: Compatibility layer between Python 2 and Python 3](http://python-future.org/)  

#### Download
The program homepage is:   
https://github.com/tsutterley/nsidc-subsetter    
A zip archive of the latest version is available directly at:    
https://github.com/tsutterley/nsidc-subsetter/archive/master.zip  

#### Disclaimer  
This program is not sponsored or maintained by the Universities Space Research Association (USRA), the National Snow and Ice Data Center (NSIDC) or NASA.  This is a work in progress and will be updated with the release of NASA ICESat-2 data.  It is provided here for your convenience but _with no guarantees whatsoever_.
