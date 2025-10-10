"""
date: 2024-04-02

Take care of AttComputer reset when colle groups change.
"""
from agenda.models.attendance import AttComputer

def reset_computer(sender, **kwargs):
    AttComputer.changed_groups = True

# pre_save
def check_week(sender, instance, **kwargs):
    """
    Check if start date of BaseEvent has changed and recompute the week if needed.
    """
    try:
        obj = sender.objects.get(pk=instance.pk)
        if obj.begin != instance.begin:
            # this can't be None here, since we change week before the call
            # to super().save()
            instance.week = instance._find_week()
    except sender.DoesNotExist:
        pass