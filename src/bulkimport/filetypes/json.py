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
        raise du.BadFileContent(
            "ligne %d, colonne %d : %s" % (e.lineno, e.colno, e.msg)) from e
    # first of all : check if json object is a list of dict
    if not isinstance(l, list):
        raise du.NotIterable(
            "le fichier contient un objet seul, une liste d'objets est attendue")
    for i, d in enumerate(l, start=1):
        if not isinstance(d, dict):
            raise du.NotIterable("l'objet n° %d n'est pas un objet" % i)
    # find keys for each dict
    keys = []
    if len(l) > 0:
        d = l[0]
        for key in d:
            keys.append(key)
    for i, d in enumerate(l[1:], start=2):
        for k in keys:
            if k not in d:
                raise du.DifferentKeys(
                    "l'objet n° %d n'a pas d'attribut %s" % (i, str(k)))
    # un json n'a pas de lignes : on numérote les objets.
    rows = [du.Row(d, line_no=i) for i, d in enumerate(l, start=1)]
    return du.DictIterable(keys, rows, position_label="objet")
