"""
date: 2024-03-26
"""
#from django import urls
from django.forms import widgets, fields, BoundField

def customize_label(more_attrs):
    """
    Returns a subclass of BoundField to be used in a field class as :

        CustomClass = customize_label(attrs)
        def get_bound_field(self, form, field_name):
            return self.CustomClass(form, self, field_name)
        
    The given attrs will be added as html attrs on label tag.
    Use keys "for" and "class" with caution
    """

    class MyBoundField(BoundField):

        def label_tag(self, attrs=None, **kwargs):
            attrs = attrs or {}
            attrs.update(more_attrs)
            return super().label_tag(attrs=attrs, **kwargs)
    
    return MyBoundField

class SliderCheckbox(widgets.CheckboxInput):

    template_name = "forms/slider_checkbox.html"
    STYLING_CLASSES = "opacity-0 w-15 h-8 pointer-events-auto peer slider-input"

    def __init__(self, attrs=None):
        attrs = attrs or {}
        if "class" in attrs:
            base_css_class = attrs["class"] + " "
        else:
            base_css_class = ""
        attrs["class"] = base_css_class + self.STYLING_CLASSES
        return super().__init__(attrs=attrs)

class SliderField(fields.BooleanField):

    widget = SliderCheckbox
    BoundFieldClass = customize_label({"class": "inline-block mr-1 h-8"});

    def get_bound_field(self, form, field_name):
        return self.BoundFieldClass(form, self, field_name)


class DateTimePicker(widgets.DateTimeInput):

    input_type = "datetime-local"

    def __init__(self, attrs=None, format="%Y-%m-%dT%H:%M") -> None:
        super().__init__(attrs, format)

class DatePicker(widgets.DateInput):

    input_type = "date"
    
    def __init__(self, attrs=None, format="%Y-%m-%d") -> None:
        super().__init__(attrs, format)

class DataSelect(widgets.Select):
    """
    Extends the Select widget to add data from instances.
    To be used with modelfields.AdvancedModelChoiceField
    """

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        choices_map = {t[0]: t for t in self.choices}
        for group_name, group_choices, group_index in context["widget"]["optgroups"]:
            for choice in group_choices:
                choice_tuple = choices_map.get(choice["value"])
                if choice_tuple is not None and hasattr(choice_tuple, "get_prop_dict"):
                    # check for attr to avoid the empty choice.
                    choice["attrs"].update(choice_tuple.get_prop_dict())
        return context

class DataListText(widgets.TextInput):
    """
    Add a datalist tag to a TextInput widget.
    """
    template_name = "forms/datalist_text.html"

    def __init__(self, datalist=None, attrs=None):
        if datalist is None:
            raise ValueError("datalist must be provided")
        
        super().__init__(attrs=attrs)
        self.datalist = datalist
    
    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context["widget"]["datalist"] = self.datalist
        return context
    
    def render(self, name, value, attrs=None, renderer=None):
        if attrs is None or "id" not in attrs:
            raise ValueError("attrs must be provided with an id")
        attrs["list"] = attrs["id"] + "_datalist"
        return super().render(name, value, attrs, renderer)

class DeleteCheckbox(widgets.CheckboxInput):
    """
    A checkbox input for deletable formset forms.
    Renders a hidden input with value "" before the checkbox input.
    """