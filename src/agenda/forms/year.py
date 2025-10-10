"""
date: 2024-02-26
"""
from django import forms

from agenda.models import year

class GenerateWeeks(forms.Form):
    begin = forms.DateField(label="1er jour")
    end = forms.DateField(label="Dernier jour")
    make_default = forms.BooleanField(label="Année courante", required=False)

    def save(self):
        if not self.is_valid():
            raise forms.ValidationError("Données invalides")
        gen = year.HolidayGenerator()
        cd = self.cleaned_data
        if cd["make_default"]:
            year.Week.objects.active().update(active=False)
        return gen.generate_between(cd["begin"], cd["end"], active=cd["make_default"])

