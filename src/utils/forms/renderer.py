"""
date: 2024-02-26
"""

from django.forms import renderers

class CustomRenderer(renderers.TemplatesSetting):
    form_template_name = "forms/div.html"
    formset_template_name = "forms/formset_div.html"
    field_template_name = "forms/field.html"
