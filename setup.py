from setuptools import setup, find_packages
setup(
	name='nsidc-subsetter',
	version='1.0.0.5',
	description='Program for using the NSIDC subsetter api for retrieving NASA Operation IceBridge, ICESat and ICESat-2 data',
	url='https://github.com/tsutterley/nsidc-subsetter',
	author='Tyler Sutterley',
	author_email='tsutterl@uw.edu',
	license='MIT',
	classifiers=[
		'Development Status :: 3 - Alpha',
		'Intended Audience :: Science/Research',
		'Topic :: Scientific/Engineering :: Physics',
		'License :: OSI Approved :: MIT License',
		'Programming Language :: Python :: 2',
		'Programming Language :: Python :: 2.7',
	],
	keywords='NSIDC Earthdata IceBridge ICESat ICESat-2 subsetting',
	packages=find_packages(),
	install_requires=['numpy','future','lxml','gdal','shapely','pyproj','fiona','geopandas'],
)
