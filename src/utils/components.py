"""
date: 2024-02-29

Base class for additional actions currently available
"""
from django import template

class TemplateDescriptor():

    def __get__(self, obj, obj_type=None):
        if not hasattr(self, "__template"):
            self.__template = template.loader.get_template(obj.template_name)
        return self.__template
    
    def __set__(self, obj, value):
        # prevent __init__ or other methods to override template
        raise AttributeError("Don't override template attribute")

class HTMLRender():
    template_name = ""
    template = TemplateDescriptor()

    def render(self) -> str:
        ctx = self.get_context_data()
        ctx["self"] = self
        return self.template.render(ctx)
    
    def get_context_data(self) -> dict:
        return {}

class Component(HTMLRender):
    """
    Simple wrapper around django template.

    Define class attribute template_name.
    The rendering context is the return value of get_context_data()
    with the addition of "self"

    Don't use template attribute for custom data.
    """

    def __str__(self):
        return self.render()