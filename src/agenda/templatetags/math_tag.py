"""
Created on Tue Dec  1 22:39:40 2015
"""

from django import template

register = template.Library()

@register.simple_tag
def divide(nb1, nb2, percent=False):
    res = nb1 / nb2
    if percent:
        return "{percent:.2%}".format(percent=res)
    else:
        return "{res:f}".format(res=res)

@register.simple_tag
def multiply(nb1, nb2):
    return nb1*nb2 #"{res:f}".format(res=nb1*nb2)