"""
date: 2024-05-14
"""

from functools import partial

from django.forms import models
from django.forms.fields import ChoiceField, MultipleChoiceField

from . import widgets

SliderField = widgets.SliderField

def get_related_attr(instance, attr):
    """
    Mimic django related query to get attr
    """
    parts = attr.split("__")
    res = instance
    for part in parts:
        res = getattr(res, part)
    return res

def tuple_factory(keys):
    class MyTuple(tuple):

        def get_prop_dict(self):
            """
            Returns a dict of required properties, in HTML data- format
            """
            if not hasattr(self, "instance"):
                return {}
            d = {}
            for key in keys:
                d["data-" + key] = get_related_attr(self.instance, key)
            return d

    return MyTuple

class AdvancedModelChoiceIterator(models.ModelChoiceIterator):
    """
    Iterator to use with the 2 following classes
    """

    def __init__(self, *args, keys=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.TupleClass = tuple_factory(keys or [])

    def choice(self, obj):
        t = self.TupleClass((self.field.prepare_value(obj), self.field.label_from_instance(obj)))
        t.instance = obj
        return t


class AdvancedModelChoiceField(models.ModelChoiceField):
    """
    Form Choice field which populate choices with object data in addition to
    pk and label

    Each choice will have a get_prop_dict method which returns a dict.

    data_keys are a list of strings suitable to be query filters on the base model
    of the choices.

    The dict returned by get_prop_dict will have keys like data-{key} and values
    fetched from the related object following django convention for related models.

    books = AdvancedModelChoiceField(
        queryset=Book.objects.all(),
        data_keys=["author__name"])
    We can then output in html data-author__name="..." for each choice 
    """

    widget = widgets.DataSelect
    def __init__(self, *args, data_keys=None, **kwargs):
        self.data_keys = data_keys or []  # _get_choices used in super().__init__
        super().__init__(*args, **kwargs)

    def _get_choices(self):
        if hasattr(self, "_choices"):
            return self._choices
        return AdvancedModelChoiceIterator(self, keys=self.data_keys)

    choices = property(_get_choices, ChoiceField.choices.fset)


# class AdvancedModelMultipleChoiceField(models.ModelMultipleChoiceField):
#     """
#     Same as above, but for MultipleChoice fields
#     """
#     widget = widgets.DataSelect
#     def __init__(self, *args, data_keys=None, **kwargs):
#         self.data_keys = data_keys or []  # _get_choices used in super().__init__
#         super().__init__(*args, **kwargs)

#     def _get_choices(self):
#         if hasattr(self, '_choices'):
#             return self._choices

#         return AdvancedModelChoiceIterator(self, keys=[])

#     choices = property(_get_choices, MultipleChoiceField.choices.fset)


def choice_field_factory(data_keys, **kwargs):
    """
    Utility function to create a class with given keys.
    Use with field_classes in Meta class of a form
    """
    return partial(AdvancedModelChoiceField, data_keys=data_keys, **kwargs)

# def multiple_choice_field_factory(data_keys, **kwargs):
#     return partial(AdvancedModelMultipleChoiceField, data_keys=data_keys, **kwargs)