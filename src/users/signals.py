"""
date: 2024-12-17
Update custom fields when a user is marked as inactive
"""

def update_custom_fields(sender, instance, **kwargs):
    """
    Called as pre_save signal
    """
    if not instance.is_active:
        instance.roles.reset()

def invalid_user_cache(sender, instance, **kwargs):
    """
    Called as post_save signal
    """
    from .cache import teachers, colleurs, subjects
    teachers.stale = True
    colleurs.stale = True

def invalid_subject_cache(sender, instance, **kwargs):
    """
    Called as post_save signal
    """
    from .cache import subjects
    subjects.stale = True