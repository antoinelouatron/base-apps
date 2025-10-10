"""
Created on Fri Oct 16 17:55:08 2015
"""
from django import urls

class ViewList():

    def __init__(self):
        self.views = {}
        self.urlpatterns = []

    def register(self, view_name: str, name: str, cls):
        """
        Register a new import view to be displayed in main import page.
        name is an optionnal label for the generated link.
        """
        if view_name in self.views:
            raise ValueError("Same view name")
        self.views[view_name] = name
        self.urlpatterns.append(
            urls.path(view_name, cls.as_view(), name=view_name))
    
    def unregister(self, view_name: str):
        """
        Unregister a view
        """
        if view_name not in self.views:
            raise ValueError("View not registered")
        del self.views[view_name]

    def get_urls(self):
        res_urls = []
        for v, n in self.views.items():
            res_urls.append((urls.reverse("import:" + v), n))
        return res_urls

_vl = ViewList()

register = _vl.register
unregister = _vl.unregister
get_urls = _vl.get_urls
urlpatterns = _vl.urlpatterns
