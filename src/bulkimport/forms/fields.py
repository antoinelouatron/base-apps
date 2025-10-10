"""
Created on Fri Sep 25 17:33:55 2015
"""

import django.forms.fields

import bulkimport.forms.widgets


class NameMappingField(django.forms.fields.MultiValueField):
    """
    A collection of label to name mapping
    normalize to a dict str -> str where keys are fields_names and values the corresponding names.

    Takes a required argument : fields_name which are the labels to be mapped.
    """

    def __init__(self, name_fields_names, *args, add_attrs=None, **kwargs):
        fields = []
        add_attrs = add_attrs or {}
        self. _nfn = name_fields_names
        self.auto_populate = kwargs.pop("auto_populate")
        for name in name_fields_names:
            f = django.forms.fields.CharField(label=name)
            fields.append(f)
        if self.auto_populate:
            kwargs["initial"] = name_fields_names
        kwargs["widget"] = bulkimport.forms.widgets.NameMappingWidget(fields, add_attrs=add_attrs)
        super().__init__(*args, fields=fields, **kwargs)

    def compress(self, data_list):
        d = {}
        for i in range(len(data_list)):
            d[data_list[i]] = self._nfn[i]
        return d
