"""
Created on Thu Mar  5 12:18:46 2015
"""

import collections.abc
import json
import logging

from django.conf import settings
from django.templatetags.static import static

from utils.components import Component

logger = logging.getLogger("assets-manager")

class AssetsLoader():
    """
    Class to load assets from a json file.
    The file must contain a dict with keys "SCRIPTS" and "STYLES"
    Each key must contain a dict with keys being the asset name and values
    the asset passed to webpack-loader.
    """

    def __init__(self, fname=None):
        self.scripts = {}
        self.styles = {}
        if fname is None:
            fname = settings.ASSETS_MAP
        try:
            with open(fname, "r") as f:
                data = json.load(f)
            self.scripts = data.get("SCRIPTS", {})
            self.styles = data.get("STYLES", {})
        except Exception as e:
            logger.warning("Could not load assets map from {}: {}".format(fname, e))
        try:
            with open(settings.VITE_ALIAS_MAP, "r") as f:
                self.aliases = json.load(f)
        except Exception as e:
            logger.warning("Could not load vite alias map from {}: {}".format(
                settings.VITE_ALIAS_MAP, e))
            self.aliases = {}

    def _resolve(self, name: str) -> str:
        """
        Resolve aliases in the given name.

        Used for dev serving with vite.
        """
        if name is None:
            return None
        for alias, path in self.aliases.items():
            if name.startswith(alias):
                return path + name[len(alias):]
        return name
    
    def _get_with_code(self, name: str, code_map: dict) -> str:
        code = code_map.get(name)
        if code is None:
            log_func = logger.error if settings.MISSING_ASSET_LOG_LEVEL == "error" else logger.warning
            log_func("Asset {} not found in assets map".format(name))
            return None
        return self._resolve(code)

    def get_script(self, name):
        return self._get_with_code(name, self.scripts)

    def get_style(self, name):
        return self._get_with_code(name, self.styles)

_loader = AssetsLoader()

class AssetManager():
    """
    Collection of scripts and stylesheets to add in <head></head>
    """

    def __init__(self):
        self.styles = []
        self.scripts = []
        self.print_styles = []
        self.workers = {}

    def update_context(self, context):
        """
        update given context/dict with keys :
        - head_scripts
        - styles_list
        - print_styles

        debug scripts are placed after main scripts
        """
        context["script_list"] = [ sc for sc in self.scripts if sc]
        context["style_list"] = self.styles
        context["print_styles"] = self.print_styles

    def add_scripts(self, *scripts, code=False):
        """
        Add script names in this manager.
        returns self
        """
        if code:
            scripts = [_loader.get_script(sc) for sc in scripts]
            scripts = [sc for sc in scripts if sc is not None]
        for sc in scripts:
            self.scripts.append(sc)
        return self

    def add_styles(self, *styles, print_style=False):
        """
        Add style sheets. If print_style is True, add them to print styles

        returns self
        """
        L = self.print_styles if print_style else self.styles
        for st in styles:
            L.append(st)
        return self

    def _replace(self, prop, fname, hint=None):
        L = getattr(self, prop, [])
        if hint is None:
            L.append(fname)
            setattr(self, prop, L)
            return self
        replaced = False
        for i in range(len(L)):
            if hint in L[i]:
                replaced = True
                L[i] = fname
                break
        if not replaced:
            L.append(fname)
        setattr(self, prop, L)
        return self

    def replace_style(self, fname, hint=None, print_style=False):
        name = "styles"
        if print_style:
            name = "print_" + name
        return self._replace(name, fname, hint=hint)

    def replace_script(self, fname, hint=None):
        name = "scripts"
        return self._replace(name, fname, hint=hint)

    # def worker_url(self):
    #     return static("js/webpush/service-worker.js")

    def add_worker(self, name: str, worker_url: str) -> "AssetManager":
        """
        Add a worker to the list of workers
        """
        self.workers[name] = static(worker_url)
        return self
    
    def worker_urls(self) -> dict[str, str]: 
        """
        Return the list of worker urls
        """
        return self.workers


class NsData(collections.abc.Mapping, Component):
    """
    Class responsible for storage and js output of key/values pairs to transmit
    to javascript via the namespace object.

    Use dot notation for keys to get/set values. Do not set self-referencing dict as values

    dict values are incorporated in self
    """
    template_name = "components/nsdata.html"

    def __init__(self, *args, warning=lambda x: x):
        self._dic = {}
        self.warning = warning
        for arg in args:
            self.append(arg)
    
    # for backward compatibility with tuple list
    def extend(self, L):
        for el in L:
            self.append(el)

    # for backward compatibility with tuple list
    def append(self, t):
        if len(t) != 2:
            raise ValueError("Can't append a tuple of len {}".format(len(t)))
        self[t[0]] = t[1]
    
    def __bool__(self):
        return bool(self._dic)

    @property
    def data(self):
        # convert to dict
        return {k: v.data if isinstance(v, NsData) else v
                for k, v in self._dic.items()}

    def __iter__(self):
        for k, v in self._dic.items():
            if isinstance(v, NsData):
                empty = True
                for key in v.keys():
                    empty = False
                    yield k + "." + key
                if empty:
                    yield k
            else:
                yield k

    def __len__(self):
        return len(list(iter(self)))

    def __bool__(self):
        return bool(self._dic)

    def __repr__(self):
        L = ["('{}', {})".format(k, repr(v)) for k, v in self._dic.items()]
        return "NsData({})".format(",".join(L))

    def __getitem__(self, key):
        """
        Traverse through dotted notation for keys.
        The end point must be "real" value ie no dict.
        """
        if not isinstance(key, str):
            raise TypeError("Keys for NsData objects must be strings.")
        parts = key.split(".")
        # only work with underlying dict
        curr_d = self._dic
        for p in parts:
            curr_d = curr_d.get(p)  # don't throw key error with only a part of the path
            if curr_d is None:
                raise KeyError(key)
            if isinstance(curr_d, NsData):
                curr_d = curr_d._dic
        # test if we traversed to a leaf. Only leafs contains actual data
        if isinstance(curr_d, NsData) and curr_d:
            raise KeyError("No data for key {}".format(key))
        return curr_d

    def __setitem__(self, key, value):
        if not isinstance(key, str):
            raise TypeError("Keys for NsData objects must be strings.")
        if isinstance(value, dict):
            str_dic = bool(value) # set empty dict as is
            # special case for string ony dicts set as values, we extend
            # the current namespace
            for k in value.keys():
                str_dic = str_dic and isinstance(k, str)
            if str_dic:
                for k, v in value.items():
                    self[key + "." + k] = v
                return
        parts = key.split(".")
        curr_d = self
        for i in range(len(parts) - 1):
            p = parts[i]
            if p in curr_d._dic:
                curr_d = curr_d._dic[p]
            else:  # create appropriate path
                curr_d._dic[p] = NsData()
                curr_d = curr_d._dic[p]
            if not isinstance(curr_d, NsData):
                # trying to set a child value which will erase some already set value
                raise ValueError("Key already set : {}".format(".".join(parts[:i+1])))
        if parts[-1] in curr_d._dic:
            self.warning((key, value))
        if value == {}:
            value = NsData()
        curr_d._dic[parts[-1]] = value

    def __delitem__(self, key):
        if not isinstance(key, str):
            raise TypeError("Keys for NsData objects must be strings.")
        parts = key.split(".")
        curr_d = self._dic
        for p in parts[:-1]:
            curr_d = curr_d.get(p)
            if curr_d is None:
                raise KeyError(key)
            curr_d = curr_d._dic
        del curr_d[parts[-1]]
