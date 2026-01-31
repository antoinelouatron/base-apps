"""
date: 2026-01-19
"""

from django import forms

class CscopeFilterForm(forms.Form):

    add_css_classes = {
        "min_week": "w-40",
        "max_week": "w-40",
    }
    
    min_week = forms.IntegerField(required=False, label="Semaine min",
        widget=forms.NumberInput(attrs={"class": "w-40"}))
    max_week = forms.IntegerField(required=False, label="Semaine max",
        widget=forms.NumberInput(attrs={"class": "w-40"}))