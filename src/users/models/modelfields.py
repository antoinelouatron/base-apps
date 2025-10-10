"""
date: 2025-09-15
"""
from django.core.exceptions import ValidationError
from django.db import models

def validate_description_list(value):
    if not isinstance(value, list):
        raise ValidationError("La valeur doit être une liste")
    names = set()
    for item in value:
        if not isinstance(item, dict):
            raise ValidationError("Chaque élément doit être un dictionnaire")
        if "name" not in item or not isinstance(item["name"], str) or item["name"] in names:
            raise ValidationError("Chaque élément doit avoir une clé 'name' de type str")
        if "description" in item and not isinstance(item["description"], str):
            raise ValidationError("La clé 'description', si présente, doit être de type str")
        names.add(item["name"])

class DescriptionListField(models.JSONField):
    """
    JSONField for lists of {name: str, description: str?} items.
    Names must be unique.
    """

    def __init__(self, *args, **kwargs):
        defaults = {"default": list, "validators": [validate_description_list]}
        defaults.update(kwargs)
        super().__init__(*args, **defaults)

def validate_subgrades_dict(value):
    if not isinstance(value, dict):
        raise ValidationError("La valeur doit être un dictionnaire")
    for k, v in value.items():
        if not isinstance(k, str):
            raise ValidationError("Les clés doivent être des chaînes de caractères")
        try:
            float(v)
        except (ValueError, TypeError):
            raise ValidationError("Les valeurs doivent être des nombres")

class SubGradesField(models.JSONField):
    """
    JSONField for dict of {subgrade_name: max_grade}
    """

    def __init__(self, *args, **kwargs):
        defaults = {"default": dict, "validators": [validate_subgrades_dict]}
        defaults.update(kwargs)
        super().__init__(*args, **defaults)