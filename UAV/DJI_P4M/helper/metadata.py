#!/usr/bin/env python
# coding: utf-8

# References: 
# MicaSense RedEdge and Altum Image Processing Tutorials (https://github.com/micasense/imageprocessing)https://github.com/micasense/imageprocessing)

"""
RedEdge Metadata Management Utilities

Copyright 2017 MicaSense, Inc.

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in the
Software without restriction, including without limitation the rights to use,
copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the
Software, and to permit persons to whom the Software is furnished to do so,
subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""

# Support strings in Python 2 and 3
from __future__ import unicode_literals

import os
import exiftool


class Metadata(object):
    """ Container for DJI P4M image metadata"""

    def __init__(self, filename, exiftool_path=None, exiftool_obj=None):
        if exiftool_obj is not None:
            self.exif = exiftool_obj.get_metadata(filename)
            return
        if exiftool_path is not None:
            self.exiftoolPath = exiftool_path
        elif os.environ.get('exiftoolpath') is not None:
            self.exiftoolPath = os.path.normpath(os.environ.get('exiftoolpath'))
        else:
            self.exiftoolPath = None
        if not os.path.isfile(filename):
            raise IOError("Input path is not a file")
        with exiftool.ExifTool(self.exiftoolPath) as exift:
            self.exif = exift.get_metadata(filename)

    def get_all(self):
        """ Get all extracted metadata items """
        return self.exif

    def get_item(self, item, index=None):
        """ Get metadata item by Namespace:Parameter"""
        val = None
        try:
            val = self.exif[item]
            if index is not None:
                try:
                    if isinstance(val, unicode):
                        val = val.encode('ascii', 'ignore')
                except NameError:
                    # throws on python 3 where unicode is undefined
                    pass
                if isinstance(val, str) and len(val.split(',')) > 1:
                    val = val.split(',')
                val = val[index]
        except KeyError:
            pass
        except IndexError:
            print("Item {0} is length {1}, index {2} is outside this range.".format(
                item,
                len(self.exif[item]),
                index))
        return val

    def size(self, item):
        """get the size (length) of a metadata item"""
        val = self.get_item(item)
        try:
            if isinstance(val, unicode):
                val = val.encode('ascii', 'ignore')
        except NameError:
            # throws on python 3 where unicode is undefined
            pass
        if isinstance(val, str) and len(val.split(',')) > 1:
            val = val.split(',')
        if val is not None:
            return len(val)
        else:
            return 0

    def print_all(self):
        for item in self.get_all():
            print("{}: {}".format(item, self.get_item(item)))
            