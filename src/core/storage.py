# -*- coding: utf-8 -*-
"""
Created on Fri Sep  6 14:59:16 2019

@author: antoine
"""

from django.contrib.staticfiles.storage import ManifestStaticFilesStorage
import logging


class ForgivingManifestStaticFilesStorage(ManifestStaticFilesStorage):

    manifest_strict = False
    logger = logging.getLogger("django.request")

    def hashed_name(self, name, content=None, filename=None):
        try:
            result = super().hashed_name(name, content, filename)
        except ValueError:
            # When the fille is missing, let's forgive and ignore that.
            # print("Missing file : " + name)
            self.logger.info("Missing file : {}".format(name))
            result = name
        return result
