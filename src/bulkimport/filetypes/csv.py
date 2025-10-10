# -*- coding: utf-8 -*-
"""
Created on Sun Sep 27 13:50:22 2015

@author: antoine
"""

import csv

import bulkimport.dict_utils as du


def _formatter(d):
    # output only d values
    return '"' + ' '.join(str(k) + ' : ' + str(v)
                          for k, v in d.items()) + '"'

def guess_delimiter(line: str) -> str:
    """
    Guess the delimiter of a CSV line.
    """
    # find counts for common delimiters and return the one with the highest count
    delimiters = [";", "\t"]
    delim = ","
    count = line.count(delim)
    for d in delimiters:
        c = line.count(d)
        if c > count:
            delim = d
            count = c
    return delim

def get_seq(file):
    for line in file:
        delim = guess_delimiter(line)
        file.seek(0)  # reset file pointer to the beginning
        # use the guessed delimiter to read the CSV
        file.seek(0)
        break
    reader = csv.DictReader(file, delimiter=delim)
    return du.DictIterable(reader.fieldnames, reader, formatter=_formatter)
