#!/usr/bin/python

# This is a Python script to download HD trailers from the Apple Trailers
# website. It uses the "Just Added" JSON endpoint to discover new trailers and
# keeps track of the ones it has already downloaded so they aren't
# re-downloaded.
#
# Started on: 10.14.2011
#
# Copyright 2011-2013 Adam Goforth
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# Some imports are declared inside of functions, so other functions in this
# script can be used in other scripts, without requiring all of
# the dependencies.
import re
import urllib
import urllib2
import os.path
import shutil
from bs4 import BeautifulSoup

#############
# Functions #
#############
def getTrailerFileUrl(pageUrl, res):
    """Take a trailer page URL and convert it to the URL of the trailer .mov file in the desired resolution"""
    """The trailer file URL is pulled out of a JSON file on the server."""
    resSegment = "extralarge"
    if (res == '480'):
        resSegment = "large"

    incUrl = pageUrl + 'includes/trailer/' + resSegment + '.html'
    incPage = urllib.urlopen(incUrl)
    incContents = incPage.read()
    incSoup = BeautifulSoup(incContents)
    links = incSoup.findAll('a', 'movieLink')

    if (len(links) != 1):
        # Some trailers might only have a 480p file
        if res != '480':
            print "Could not find a trailer file URL with resolution '%s'. Retrying with '480'" % res
            return getTrailerFileUrl(pageUrl, '480')
        print "Error finding the trailer file URL"
        return ""

    url = links[0]['href']

    # Change link URL to the download URL by changing e.g. _720p to _h720p
    url = re.sub('_(\d+)p', '_h\\1p', url)

    return url

def getTrailerTitle(pageUrl):
    """Take a trailer page URL and return the title of the film, taken from the title tag on the page"""
    trPage = urllib.urlopen(pageUrl)
    trContents = trPage.read()
    trSoup = BeautifulSoup(trContents)
    titleTag = trSoup.html.head.title.string

    titleParts = titleTag.split(' - ')
    return titleParts[0]

def getDownloadedFiles(dlListPath):
    """Get the list of downloaded files from the text file"""
    fileList = []
    if (os.path.exists(dlListPath)):
        f = open(dlListPath, 'r')
        for line in f.xreadlines():
            fileList.append(line.strip())
        f.close()
    return fileList

def writeDownloadedFiles(fileList, dlListPath):
    """Write the list of downloaded files to the text file"""
    f = open(dlListPath, 'w')
    newList = [filename + "\n" for filename in fileList]
    f.writelines(newList)
    f.close()

def recordDownloadedFile(filename, dlListPath):
    """Appends the given filename to the text file of already downloaded files"""
    fileList = getDownloadedFiles(dlListPath)
    fileList.append(filename)
    writeDownloadedFiles(fileList, dlListPath)

def downloadTrailerFile(url, destdir, filename):
    """Accepts a URL to a trailer video file and downloads it"""
    """You have to spoof the user agent or the site will deny the request"""
    user_agent = 'QuickTime/7.6.2'
    data = None
    headers = { 'User-Agent' : user_agent }
    req = urllib2.Request(url, data, headers)
    f = urllib2.urlopen(req)

    filePath = destdir + filename
    # Buffer 1MB at a time
    chunkSize = 1024 * 1024
    with open(filePath, 'wb') as fp:
        shutil.copyfileobj(f, fp, chunkSize)

def downloadTrailerFromPage(pageUrl, title, dlListPath, res, destdir):
    """Takes a page on the Apple Trailers website and downloads the trailer for the movie on the page"""
    """Example URL: http://trailers.apple.com/trailers/lions_gate/thehungergames/"""
    print "Checking for " + title
    trailerUrl = getTrailerFileUrl(pageUrl, res)
    trailerFileName = title + ".Trailer." + res + "p.mov"
    downloadedFiles = getDownloadedFiles(dlListPath)
    if trailerUrl != "":
        if not trailerFileName in downloadedFiles:
            print "downloading " + trailerUrl
            downloadTrailerFile(trailerUrl, destdir, trailerFileName)
            recordDownloadedFile(trailerFileName, dlListPath)
        else:
            print "*** File already downloaded, skipping: " + trailerFileName

def getConfigValues():
    """Get the script's configuration values and return them in a dict
    
    If a config file exists, merge its values with the defaults. If no config
    file exists, just return the defaults. Validates the settings in the
    config file and raises a ValueError exception if any of the given settings
    are invalid.
    
    """
    from ConfigParser import SafeConfigParser

    scriptDir = os.path.abspath(os.path.dirname(__file__))
    configPath = "%s/settings.cfg" % scriptDir
 
    config = SafeConfigParser(
        defaults = {
            'resolution': '720',
            'download_dir': scriptDir
        }
    )
    configValues = config.defaults()

    if (configValues['download_dir'][-1] != '/'):
        configValues['download_dir'] = '%s/' % configValues['download_dir']

    if (not os.path.exists(configPath)):
        print "No config file found.  Using default values."
        print "    Resolution: %sp" % configValues['resolution']
        print "    Download Directory: %s" % configValues['download_dir']
    else:
        config.read(configPath)

        configValues = config.defaults()
        validResolutions = ['480', '720']

        # Validate the config options
        if configValues['resolution'] not in validResolutions:
            resString = ", ".join(validResolutions)
            raise ValueError('Invalid resolution. Valid values: %s' % resString)

        if (len(configValues['download_dir']) < 1) or (not os.path.exists(configValues['download_dir'])):
            raise ValueError('The download directory must be a valid path')

    return configValues


#############
# Main Prog #
#############
if __name__ == '__main__':
    import argparse
    import json
    
    parser = argparse.ArgumentParser(description=
            'Download movie trailers from the Apple website. ' +
            'With no arguments, will download all of the trailers in the current RSS feed. ' +
            'When a trailer page URL is specified, will only download the single trailer at that URL. ' + 
            '\n\nExample URL: http://trailers.apple.com/trailers/lions_gate/thehungergames/')
    parser.add_argument('-u', action="store", dest="url", help="The URL of the Apple Trailers web page for a single trailer.")
    results = parser.parse_args()
    page = results.url

    try:
        config = getConfigValues()
    except ValueError as e:
        print "Configuration error: " + str(e)
        print "Exiting..."
        exit()

    dlListPath = config['download_dir'] + "download_list.txt"

    # Do the download
    if page != None:
        # The trailer page URL was passed in on the command line
        trailerTitle = getTrailerTitle(page)
        downloadTrailerFromPage(page, trailerTitle, dlListPath, config['resolution'], config['download_dir'])

    else:
        # Use the "Just Added" JSON file
        newestTrailers = json.load(urllib.urlopen('http://trailers.apple.com/trailers/home/feeds/just_added.json'))
    
        for trailer in newestTrailers:
            url = "http://trailers.apple.com" + trailer["location"]
            downloadTrailerFromPage(url, trailer["title"], dlListPath, config['resolution'], config['download_dir'])
