"""
Created on Sat Sep 26 19:23:33 2015
"""

def map_keys(d, key_mapping):
    """
    Change keys in d.

    key_mapping must be a dictionnary of hashable -> replacement
    Each key in d found as a key in key_mapping is replaced by the value in key_mapping.

    If replacement is None, d[key] will be deleted.

    No check for key duplication is made.
    """
    for old_key in key_mapping:
        if old_key in d:
            if key_mapping[old_key] is None:
                del d[old_key]
            else:
                d[key_mapping[old_key]] = d.pop(old_key)
    return d


class DictIterable():
    """
    Simple wrapper around an iterable of dict.
    The use case is when all dict have same keys, and the first parameter is an iterable of
    these keys.

    optionnal parameter formatter is a function taking a dict and returning a string representing
    this dict (useful to represent dict extracted from file)
    """

    def __init__(self, keys, dict_iterable, formatter=str):
        self.keys = list(keys)
        self._data = dict_iterable
        self.formatter = formatter

    def __iter__(self):
        return self._data.__iter__()


class NotIterable(Exception):
    """
    Exception to raise when a construction of DictIterable fails.
    """
    pass


class DifferentKeys(KeyError):
    pass

def is_injection(d, E, F):
    """
    Check if dictionary d is an injection from sequences E to F.

    E must be the keys and F the values of d.
    >>> d = {'a': 1, 'b': 2}
    >>> is_injection(d, 'ab', (1,1))
    False
    >>> is_injection(d, 'ab', (1,3))
    False
    >>> is_injection(d, 'ac', (1,3))
    False
    >>> is_injection(d, 'ac', (1,2))
    False
    >>> is_injection(d, 'ab', (1,2))
    True
    >>> is_injection(d, 'ab', (1,2,3))
    True
    """
    n = len(d)
    if len(E) != n:
        return False
    occurrences = {}
    for f in F:
        occurrences[f] = False  # has this element been encountered yet
    for e in E:
        if e not in d:
            return False
        oc = occurrences.get(d[e], True)  # if d[e] is not an element of F, oc == True
        if oc:
            return False
        occurrences[d[e]] = True
    return True

def is_bijection(d, E, F):
    """
    Check if dictionary d is a bijection between sequences E and F.

    E must be the keys ans F the values of d.
    >>> d = {'a': 1, 'b': 2}
    >>> is_bijection(d, 'ab', (1,1))
    False
    >>> is_bijection(d, 'ab', (1,3))
    False
    >>> is_bijection(d, 'ac', (1,3))
    False
    >>> is_bijection(d, 'ac', (1,2))
    False
    >>> is_bijection(d, 'ab', (1,2))
    True
    """
    n = len(d)
    if len(E) != n or len(F) != n:
        return False
    return is_injection(d, E, F)