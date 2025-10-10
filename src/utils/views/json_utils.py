"""
Created on Sun Jan 11 15:32:56 2015
"""

from django.conf import settings

ERROR = "ERROR"
OK = "OK"

JSON_CONTEXT = {"error": ERROR, "ok": OK}


def error_data(exc, add_data={}):
    """
    Returns a dictionary suitable to use for json response.
    """
    data = {"status": ERROR}
    if settings.DEBUG:
        data["error"] = str(exc)
    elif not isinstance(exc, str):
        data["error"] = "Une erreur s'est produite"
    else:
        data["error"] = exc
    data.update(add_data)
    return data


def json_data(data_dict=None, **kwargs):
    """
    Returns a dict with OK status and given data.
    kwargs take precedence over data_dict
    """
    data = {"status": OK}
    if data_dict is not None:
        data.update(data_dict)
    data.update(kwargs)
    return data
