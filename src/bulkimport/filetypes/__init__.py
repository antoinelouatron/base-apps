# -*- coding: utf-8 -*-
"""
Created on Sun Sep 27 10:37:32 2015

To add support for a file type (identified by his extension), simply add a module in this package
with name <extension>.py. This module must provide a get_seq function which takes a file object
as only parameter and returns a DictIterable.

Les dict produits gagnent à être des dict_utils.Row : ils portent alors leur
position dans le fichier, que les messages d'erreur reprennent.


@author: antoine
"""

import importlib
import os.path
import pkgutil

from bulkimport.dict_utils import (
    BadFileContent, DifferentKeys, EmptyFile, ImportFileError, NoHeader,
    NotIterable,
)

__all__ = ['load', 'NotSupportedExtension', 'NotIterable', 'ImportFileError',
           'BadFileContent', 'EmptyFile', 'NoHeader', 'DifferentKeys',
           'supported_extensions', 'SPREADSHEET_EXTENSIONS']

# Déposer un classeur au lieu d'un csv est l'erreur la plus fréquente : on la
# reconnait pour pouvoir expliquer comment exporter, plutôt que de répondre
# « format non géré ».
SPREADSHEET_EXTENSIONS = frozenset(
    [".xlsx", ".xls", ".ods", ".numbers", ".gnumeric"])


class NotSupportedExtension(Exception):

    def __init__(self, msg="", *, extension="", supported=()):
        # message reste le nom du fichier : du code existant s'en sert.
        self.message = msg
        self.extension = extension
        self.supported = list(supported)


def supported_extensions() -> list[str]:
    """
    Extensions gérées, déduites des modules présents dans ce paquet.
    """
    return sorted(
        "." + mod.name
        for mod in pkgutil.iter_modules(__path__)
        if not mod.name.startswith("_")
    )


class FileConverter():

    def __init__(self):
        self._modules = {}

    def load(self, file, filename):
        _, ext = os.path.splitext(filename)
        # les fichiers venus de Windows arrivent souvent en DONNEES.CSV
        ext = ext.lower()
        if ext == '':
            raise NotSupportedExtension(
                filename, extension="", supported=supported_extensions())
        try:
            if ext in self._modules:
                mod = self._modules[ext]
            else:
                mod = importlib.import_module('%s' % ext, package='bulkimport.filetypes')
                self._modules[ext] = mod
        except ModuleNotFoundError:
            raise NotSupportedExtension(
                filename, extension=ext, supported=supported_extensions())
        # hors du try : un ImportError levé *dans* le convertisseur n'est pas
        # une extension inconnue, et le masquer rendrait la panne incompréhensible.
        return mod.get_seq(file)

_loader = FileConverter()

load = _loader.load
