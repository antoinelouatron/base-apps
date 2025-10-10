"""
Created on Thu Jul 21 10:01:16 2016
"""

import os.path

from django import template
from django.conf import settings

register = template.Library()

@register.simple_tag
def icon_url(rel_path):
    return os.path.join('/' + settings.ICON_URL.strip('/'), rel_path)

@register.simple_tag
def media_url(rel_path):
    return f"/{settings.MEDIAFILES_URL.strip('/')}/{rel_path}"

@register.simple_tag(takes_context=True)
def with_theme(context):
    if context.get("dark_theme"):
        return "?theme=dark"
    elif context.get("light_theme"):
        return "?theme=light"
    return ""
