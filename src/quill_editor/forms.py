from django import forms

from .sanitize import clean_quill_html
from .widgets import QuillWidget

__all__ = ("QuillFormField",)


class QuillFormField(forms.fields.CharField):
    def __init__(self, *args, **kwargs):
        kwargs.update(
            {
                "widget": QuillWidget(),
            }
        )
        super().__init__(*args, **kwargs)

    def clean(self, value):
        value = super().clean(value)
        return clean_quill_html(value)