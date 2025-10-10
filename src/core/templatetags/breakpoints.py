from django import template

from core.base_classes import breakpoints

register = template.Library()

@register.simple_tag
def get_class_for(breakpoint: str, element: str) -> str:
    """
    Returns the CSS class for a given breakpoint and element.
    """
    return breakpoints.get(breakpoint, {}).get(element, "")