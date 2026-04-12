import django.apps
from django.db.models.signals import post_save, post_delete, pre_save

import agenda.signals as agenda_signals
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
        post_save.connect(
            signals.invalid_user_cache,
            sender=users,
            dispatch_uid="users_invalid_cache"
        )
        post_delete.connect(
            signals.invalid_user_cache,
            sender=users,
            dispatch_uid="users_invalid_cache_delete"
        )
        post_save.connect(
            agenda_signals.reset_computer,
            sender=users,
            dispatch_uid="users_reset_computer"
        )
        post_delete.connect(
            agenda_signals.reset_computer,
            sender=users,
            dispatch_uid="users_reset_computer_delete"
        )
        subjects = django.apps.apps.get_model("users.Subject")
        post_save.connect(
            signals.invalid_subject_cache,
            sender=subjects,
            dispatch_uid="subjects_invalid_cache"
        )
        post_delete.connect(
            signals.invalid_subject_cache,
            sender=subjects,
            dispatch_uid="subjects_invalid_cache_delete"
        )