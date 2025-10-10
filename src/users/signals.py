"""
date: 2024-12-17
Update custom fields when a user is marked as inactive
"""

def update_custom_fields(sender, instance, **kwargs):
    if not instance.is_active:
        instance.teacher = False
        instance.student = False
        