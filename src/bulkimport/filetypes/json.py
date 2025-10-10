# -*- coding: utf-8 -*-
"""
Created on Sun Sep 27 10:37:32 2015

@author: antoine
"""

import json

import bulkimport.dict_utils as du


def get_seq(file):
    """
    Returns a DictIterable from a json file.

    This file must be a list of json objects having a common set of attributes.
    """
    try:
        l = json.load(file)
    except json.JSONDecodeError as e:
        raise du.NotIterable
    # first of all : check if json object is a list of dict
    if not isinstance(l, list):
        raise du.NotIterable
    keys = []
    for d in l:
        if not isinstance(d, dict):
            raise du.NotIterable
    # find keys for each dict
    if len(l) > 0:
        d = l[0]
        for key in d:
            keys.append(key)
    for d in l[1:]:
        for k in keys:
            if k not in d:
                raise du.DifferentKeys('%s non trouvé' % str(k))
    return du.DictIterable(keys, l)
