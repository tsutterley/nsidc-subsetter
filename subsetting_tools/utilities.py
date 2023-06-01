#!/usr/bin/env python
u"""
utilities.py
Written by Tyler Sutterley (05/2023)
Download and management utilities for syncing files

UPDATE HISTORY:
    Updated 05/2023: add CMR query and filter functions
    Updated 08/2021: NSIDC no longer requires authentication headers
    Updated 09/2020: generalize build opener function for different instances
    Written 09/2020
"""
from __future__ import print_function

import sys
import os
import ssl
import base64
import posixpath
import lxml.etree
import calendar,time
if sys.version_info[0] == 2:
    from cookielib import CookieJar
    import urllib2
else:
    from http.cookiejar import CookieJar
    import urllib.request as urllib2

# PURPOSE: recursively split a url path
def url_split(s):
    head, tail = posixpath.split(s)
    if head in ('http:','https:'):
        return s,
    elif head in ('', posixpath.sep):
        return tail,
    return url_split(head) + (tail,)

# PURPOSE: returns the Unix timestamp value for a formatted date string
def get_unix_time(time_string, format='%Y-%m-%d %H:%M:%S'):
    """
    Get the Unix timestamp value for a formatted date string

    Arguments
    ---------
    time_string: formatted time string to parse

    Keyword arguments
    -----------------
    format: format for input time string
    """
    try:
        parsed_time = time.strptime(time_string.rstrip(), format)
    except:
        return None
    else:
        return calendar.timegm(parsed_time)

# PURPOSE: check internet connection
def check_connection(HOST):
    """
    Check internet connection

    Arguments
    ---------
    HOST: remote http host
    """
    # attempt to connect to https host
    try:
        urllib2.urlopen(HOST,timeout=20,context=ssl.SSLContext())
    except urllib2.URLError:
        raise RuntimeError('Check internet connection')
    else:
        return True

# PURPOSE: "login" to NASA Earthdata with supplied credentials
def build_opener(username, password, context=ssl.SSLContext(),
    password_manager=True, get_ca_certs=False, redirect=False,
    authorization_header=False, urs='https://urs.earthdata.nasa.gov'):
    """
    Build ``urllib`` opener for NASA Earthdata with supplied credentials

    Arguments
    ---------
    username: NASA Earthdata username
    password: NASA Earthdata password

    Keyword arguments
    -----------------
    context: SSL context for opener object
    password_manager: create password manager context using default realm
    get_ca_certs: get list of loaded “certification authority” certificates
    redirect: create redirect handler object
    authorization_header: add base64 encoded authorization header to opener
    urs: Earthdata login URS 3 host
    """
    # https://docs.python.org/3/howto/urllib2.html#id5
    handler = []
    # create a password manager
    if password_manager:
        password_mgr = urllib2.HTTPPasswordMgrWithDefaultRealm()
        # Add the username and password for NASA Earthdata Login system
        password_mgr.add_password(None,urs,username,password)
        handler.append(urllib2.HTTPBasicAuthHandler(password_mgr))
    # Create cookie jar for storing cookies. This is used to store and return
    # the session cookie given to use by the data server (otherwise will just
    # keep sending us back to Earthdata Login to authenticate).
    cookie_jar = CookieJar()
    handler.append(urllib2.HTTPCookieProcessor(cookie_jar))
    # SSL context handler
    if get_ca_certs:
        context.get_ca_certs()
    handler.append(urllib2.HTTPSHandler(context=context))
    # redirect handler
    if redirect:
        handler.append(urllib2.HTTPRedirectHandler())
    # create "opener" (OpenerDirector instance)
    opener = urllib2.build_opener(*handler)
    # Encode username/password for request authorization headers
    # add Authorization header to opener
    if authorization_header:
        b64 = base64.b64encode('{0}:{1}'.format(username,password).encode())
        opener.addheaders = [("Authorization","Basic {0}".format(b64.decode()))]
    # Now all calls to urllib2.urlopen use our opener.
    urllib2.install_opener(opener)
    # All calls to urllib2.urlopen will now use handler
    # Make sure not to include the protocol in with the URL, or
    # HTTPPasswordMgrWithDefaultRealm will be confused.
    return opener

# PURPOSE: build string for version queries
def build_version_query(version, desired_pad_length=3):
    # check that the version is less than the required
    if (len(str(version)) > desired_pad_length):
        raise Exception(f'Version string too long: "{version}"')
    # Strip off any leading zeros
    version = int(version)
    query_params = ""
    while (len(str(version)) <= desired_pad_length):
        padded_version = str(version).zfill(desired_pad_length)
        query_params += f'&version={padded_version}'
        desired_pad_length -= 1
    # return the query parameters
    return query_params

# PURPOSE: Select only the desired data files from CMR response
def cmr_filter_json(search_page, request_type="application/x-hdf5"):
    # check that there are urls for request
    urls = list()
    if (('feed' not in search_page.keys()) or
        ('entry' not in search_page['feed'].keys())):
        return urls
    # iterate over references and get cmr location
    for entry in search_page['feed']['entry']:
        # find url for format type
        for i,link in enumerate(entry['links']):
            if ('type' in link.keys()) and (link['type'] == request_type):
                urls.append(entry['links'][i]['href'])
    return urls
