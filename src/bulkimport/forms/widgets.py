# -*- coding: utf-8 -*-
"""
Created on Fri Sep 25 18:58:53 2015

@author: antoine
"""

import django.forms.widgets
from django.utils import html
from django.forms.utils import flatatt
from django.utils.safestring import mark_safe


class LabeledTextInput(django.forms.widgets.TextInput):
    """
    Add a label to a text input
    """
    template_name = "bulkimport/labeled_input_widget.html"

    def __init__(self, *args, label='', **kwargs):
        self._label = label
        super(LabeledTextInput, self).__init__(*args, **kwargs)

    def get_context(self, name, value, attrs):
        ctx = super().get_context(name, value, attrs)
        id_attr = attrs.get('id', None)
        widget_attrs = ctx["widget"].get("attrs", {})
        if id_attr is not None:
            ctx["widget"]["label_widget"] = {
                "id": id_attr,
                "label": self._label
            }
        widget_attrs["class"] = "p-2 rounded-sm border w-40"
        return ctx


class NameMappingWidget(django.forms.widgets.MultiWidget):
    template_name = "bulkimport/name_mapping_widget.html"

    def __init__(self, fields, *args, add_attrs=None, **kwargs):
        self._name_nb = len(fields)
        attrs = {'class': "_name-field", "list": "file_keys"}
        add_attrs = add_attrs or {}
        wids = []
        for f in fields:
            w_attrs = attrs.copy()
            w_attrs.update(add_attrs.get(f.label, {}))
            label = w_attrs.get("label", f.label)
            wid = LabeledTextInput(label=label, attrs=w_attrs)
            wids.append(wid)
        super().__init__(wids, *args, **kwargs)

    def decompress(self, value):
        if value:
            return list(value.keys())
        return [None] * self._name_nb


class DataListInput(django.forms.widgets.Select):

    def render(self, name, value, attrs=None, **kwargs):
        choices = self.choices
        if value is None:
            value = ""
        id_attr = attrs.pop("id")
        attrs.update(name=name, list=id_attr, type="text", value=value)
        attrs["class"] = "p-2 rounded-sm border w-40"
        output = [html.format_html("<input{}>", flatatt(attrs)),
              html.format_html("<datalist{}>", flatatt({"id": id_attr}))]
        for choice in choices:
            output.append(html.format_html(
            "<option{value}>{label}</option>",
            value=flatatt({"value": choice[0]}), label=choice[1]))
        output.append("</datalist>")
        return mark_safe('\n'.join(output))
