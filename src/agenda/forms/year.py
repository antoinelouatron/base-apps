"""
date: 2024-02-26
"""
from django import forms
from django.db import transaction

from agenda.models import year
from utils.forms.widgets import DatePicker, SliderCheckbox

class GenerateWeeks(forms.Form):

    add_css_classes = {
        "begin": "p-1 w-1/2",
        "end": "p-1 w-1/2"
    }

    begin = forms.DateField(label="Premier jour", widget=DatePicker())
    end = forms.DateField(label="Dernier jour", widget=DatePicker())
    make_default = forms.BooleanField(label="Année courante", required=False,
        widget=SliderCheckbox)

    def save(self):
        if not self.is_valid():
            raise forms.ValidationError("Données invalides")
        gen = year.HolidayGenerator()
        cd = self.cleaned_data
        with transaction.atomic():
            if cd["make_default"]:
                year.Week.objects.active().update(active=False)
            return gen.generate_between(cd["begin"], cd["end"], active=cd["make_default"])

