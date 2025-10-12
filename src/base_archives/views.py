"""
date: 2024-10-14

Dynamic view for archive home.
"""
from django import urls
from django.conf import settings
from django.contrib import messages
from django.shortcuts import redirect

from django_sendfile import sendfile

from base_archives import db_save
from utils.views import mixins, View

class DownloadDb(mixins.UserIsStaffMixin, View):

    def get(self, request, *args, **kwargs):
        """
        Download the database.
        """
        db_name = self.request.GET.get("db_name", "default")
        try:
            db_path = db_save.get_file_path(db_name)
            command = db_save.construct_command(db_name)
            db_save.run_save_command(command)
            sendfile_path = db_path.relative_to(settings.SENDFILE_ROOT)
            return sendfile(request, str(sendfile_path),
                attachment=True, attachment_filename=db_path.name)
        except Exception as e:
            messages.error(request,
                f"Erreur lors de la sauvegarde de la base de données : {e}")
            return redirect(urls.reverse("users:account"))