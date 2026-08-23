# -*- coding: utf-8 -*-
"""
Created on Sun Sep 27 13:50:22 2015

@author: antoine
"""

import csv

import bulkimport.dict_utils as du

# Excel écrit volontiers un BOM en tête de fichier : sans nettoyage, la
# première colonne s'appelle "﻿Semaine" et reste introuvable.
BOM = "﻿"


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


def clean_header(name):
    """
    Normalise un en-tête : BOM et espaces de bordure ne doivent pas empêcher
    de reconnaitre une colonne.
    """
    if name is None:
        return name
    return name.lstrip(BOM).strip()


def get_seq(file):
    first_line = file.readline()
    if not first_line.strip():
        raise du.EmptyFile("le fichier ne contient aucune donnée")
    delim = guess_delimiter(first_line)
    file.seek(0)
    reader = csv.DictReader(file, delimiter=delim, restkey=du.EXTRA_VALUES_KEY)
    # forcer la lecture de l'en-tête maintenant : DictIterable.keys doit être
    # renseigné avant toute itération pour que le contrôle des colonnes puisse
    # s'appuyer dessus.
    fieldnames = [clean_header(n) for n in (reader.fieldnames or [])]
    if not fieldnames or all(not n for n in fieldnames):
        raise du.NoHeader("la première ligne ne contient aucun nom de colonne")
    reader.fieldnames = fieldnames

    def rows():
        try:
            for d in reader:
                yield du.Row(d, line_no=reader.line_num)
        except csv.Error as e:
            raise du.BadFileContent(str(e)) from e

    return du.DictIterable(fieldnames, rows(), position_label="ligne",
                           delimiter=delim)
