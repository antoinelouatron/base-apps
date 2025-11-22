"""
Created on Fri Jul 15 17:56:40 2016


Usage : pass a list of MenuList to context, in a variable named all_menus
Each MenuList must contain one or more MenuItems.

Each MenuItem can have a sub_menu property containing a MenuList

Only the last MenuList of all_menus will not be collapsed.
"""
import collections
import logging

from django import urls
from django.forms.utils import flatatt
import django.template.loader as tmpl_loader
from django.utils import text

logger = logging.getLogger(__name__)

class MenuItem():
    """
    Representation of an item in a menu.
    Render as <a>title</a>
    """

    BASE_ITEM_CSS_CLASS = "p-2 lg:p-1"

    def __init__(self, title, url="", active=False, data=None, name="", display=True):
        self.title = title
        self.url = url
        self.active = active
        self.data = data or {}  # html data
        self.name = name  # not displayed
        self.display = display
        self._icon_tmpl = None
        self._icon_data = {}
        self._attrs = {
            "class": self.BASE_ITEM_CSS_CLASS
        }
        self._sub_menu = False
        self.current = None # harmonize interface with MenuLIst, for breadcrumb usage

    def set_url(self, name, kwargs=None):
        """
        reverse given name with kwargs=kwargs
        """
        kwargs = kwargs or {}
        self.url = urls.reverse(name, kwargs=kwargs)
        return self

    @property
    def attrs(self):
        final_attrs = self._attrs.copy()
        if self.active:
            final_attrs["class"] += " active-menu"
        return flatatt(final_attrs)

    @attrs.setter
    def attrs(self, d):
        css_class = d.pop("class", None)
        self._attrs.update(d)
        if css_class is not None:
            css_class = " " + css_class
        else:
            css_class = ""
        self._attrs["class"] += css_class
    
    @property
    def icon(self):
        if self._icon_tmpl is None:
            return ""
        tmpl = tmpl_loader.get_template(self._icon_tmpl)
        return tmpl.render(self._icon_data)
    
    @icon.setter
    def icon(self, val):
        """
        We can set a string to be the template or a 2-uple (template, context)
        """
        try:
            tmpl, data = val
        except (TypeError, ValueError): # a length 2 string will make all that fail
            tmpl = val
            data = {}
        self._icon_tmpl = tmpl
        self._icon_data = data
    
    @property
    def sub_menu(self):
        return self._sub_menu
    
    @sub_menu.setter
    def sub_menu(self, val):
        self._sub_menu = val
        if val:
            self.data["submenu"] = True

    def __str__(self):
        return "Menu " + self.title

    def __repr__(self):
        return "MenuItem({}, url={}, active={}, data={}, name={}, display={})".format(
            self.title,
            self.url,
            self.active,
            self.data,
            self.name,
            self.display
        )

class MenuList(collections.UserList):
    """
    Represent a list of links (MenuItems)
    """

    def __init__(self, L=None, *, title=""):
        super().__init__(L)
        self._names = set()
        for item in self.data:
            self.__check_item(item)
        self.title = title
        self.current = ""

    # Type checking + uniqueness of names
    def __check_item(self, item):
        if not isinstance(item, MenuItem):
            raise TypeError("MenuList elements must be MenuItem instances")
        if item.name in self._names:
            logger.error("Duplicate menu name detected: %s", item.name)
            return False
        self._names.add(item.name)
        return True

    def __setitem__(self, i, item):
        if self.__check_item(item):
            self.data[i] = item
    
    def append(self, item):
        if self.__check_item(item):
            self.data.append(item)
    
    def add(self, title, url, name="", **url_kwargs):
        """
        Add a new item to the list
        """
        new_item = MenuItem(title, name=name)
        new_item.set_url(url, url_kwargs)
        self.append(new_item)
        return new_item

    def extend(self, other):
        newItems = other.data if isinstance(other, collections.UserList) else other
        for item in newItems:
            if self.__check_item(item):
                self.data.append(item)

    def mark_current(self, name):
        for item in self:
            item.active = item.name == name
            if item.active:
                self.current = item.title
                self._url = item.url
        return self

    def id_attr(self):
        return text.slugify(self.title)

    @property
    def url(self):
        if hasattr(self, "_url"):
            return self._url
        return ""

    def _set_display(self, name, status):
        """
        status is a boolean
        """
        for item in self:
            if item.name == name:
                item.display = status
        return self

    def show(self, name):
        return self._set_display(name, True)

    def hide(self, name):
        return self._set_display(name, False)

    def get(self, item_name):
        """
        Return an item by name, or None
        """
        for item in self:
            if item.name == item_name:
                return item

    @property
    def visible(self):
        for item in self:
            if item.display:
                yield item
