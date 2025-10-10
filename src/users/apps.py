import django.apps
from django.db.models.signals import pre_save

import users.signals as signals

class UsersConfig(django.apps.AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "users"

    def ready(self):
        users = django.apps.apps.get_model("users.User")
        pre_save.connect(
            signals.update_custom_fields,
            sender=users,
            dispatch_uid="users_update"
        )