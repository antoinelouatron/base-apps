from django.apps import AppConfig, apps
from django.db.models.signals import post_delete, post_save, pre_save

class AgendaConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "agenda"

    def ready(self):
        from . import signals
        User = apps.get_model("users.User")
        ColleGroup = apps.get_model("users.ColleGroup")
        BaseEvent = apps.get_model("agenda.BaseEvent")
        post_delete.connect(signals.reset_computer, sender=User)
        post_delete.connect(signals.reset_computer, sender=ColleGroup)
        post_save.connect(signals.reset_computer, sender=User)
        post_save.connect(signals.reset_computer, sender=ColleGroup)
        pre_save.connect(signals.check_week, sender=BaseEvent)
