"""
date: 2025-09-15
"""
import logging
from django import forms

logger = logging.getLogger(__name__)

class FilterQuerySetForm(forms.ModelForm):
    """
    A form which filters the queryset of some fields based on init args.

    Example:
        class MyForm(FilterQuerySetForm):
            my_field = forms.ModelChoiceField(queryset=MyModel.objects.all())

            class Meta:
                model = MyOtherModel
                fields = ['my_field', ...]

            def __init__(self, *args, user=None, **kwargs):
                super().__init__(*args, user=user, **kwargs)
                if user is not None:
                    self.filter_field_queryset('my_field', user=user)

        This will filter 'my_field' queryset to only include objects related to 'user'.
    """

    def filter_field_queryset(self, field_name, **filters):
        """
        Filter the queryset of a specified field using provided filters.

        Args:
            field_name (str): The name of the field to filter.
            **filters: Keyword arguments representing the filters to apply.
        """
        if field_name in self.fields:
            field = self.fields[field_name]
            if hasattr(field, 'queryset'):
                field.queryset = field.queryset.filter(**filters)
            else:
                logger.debug(f"Field '{field_name}' has no queryset to filter.")
        else:
            logger.debug(f"Field '{field_name}' is not in form.")

    def __init__(self, *args, filters=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.filters = filters or {}
        for field_name, filter_kwargs in self.filters.items():
            self.filter_field_queryset(field_name, **filter_kwargs)