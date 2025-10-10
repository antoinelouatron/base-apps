from django import template
from django.conf import settings

register = template.Library()

@register.simple_tag
def media_url(relative):
    return settings.MEDIAFILES_URL + relative.lstrip("/")

