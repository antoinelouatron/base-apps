"""
These urlpatterns must be included with namespace "import" in the main urls.py

WARNING : make sure to include bulrkimport.urls AFTER all other urls that
points to views file registering importers. Otherwise, the importers will not
export their urls. 
"""

import importlib
from django import urls
from . import importers, views


patterns = [urls.path("", views.ImportIndex.as_view(), name="index")]

app_name = "import"
# all views modules must be imported before urlpatterns
for pat in importers.urlpatterns:
    module = importlib.import_module(pat.callback.view_class.__module__)
urlpatterns = patterns + importers.urlpatterns
