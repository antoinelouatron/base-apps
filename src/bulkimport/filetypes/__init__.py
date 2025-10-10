# -*- coding: utf-8 -*-
"""
Created on Sun Sep 27 10:37:32 2015

To add support for a file type (identified by his extension), simply add a module in this package
with name <extension>.py. This module must provide a get_seq function which takes a file object
as only parameter and returns a DictIterable.


@author: antoine
"""

import importlib
import os.path

from bulkimport.dict_utils import NotIterable

__all__ = ['load', 'NotSupportedExtension', 'NotIterable']


class NotSupportedExtension(Exception):
    
    def __init__(self, msg=""):
        self.message = msg


class FileConverter():

    def __init__(self):
        self._modules = {}

    def load(self, file, filename):
        _, ext = os.path.splitext(filename)
        if ext == '':
            raise NotSupportedExtension(filename)
        try:
            if ext in self._modules:
                mod = self._modules[ext]
            else:
                mod = importlib.import_module('%s' % ext, package='bulkimport.filetypes')
                self._modules[ext] = mod
            return mod.get_seq(file)
        except ImportError:
            raise NotSupportedExtension(filename)

_loader = FileConverter()

load = _loader.load
