# -*- coding: utf-8 -*-
"""
Created on Tue Apr 21 16:38:05 2015

@author: antoine
"""

from django import template
from django.utils import html, text

register = template.Library()


@register.simple_tag
def dict_to_data(kwargs):
    """
    Convert a dict of key:string to a list of data attributes
    """
    s = ""
    for key in kwargs:
        s += 'data-{}="{}" '.format(text.slugify(key), html.escape(str(kwargs[key])))
    s = s.replace('False', 'false').replace('True', 'true')
    return html.mark_safe(s)

@register.filter
def dict_get(value: dict, key: str):
    return (value or {}).get(key, "")