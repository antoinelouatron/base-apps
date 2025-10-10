from django.db import models

from django.db import models

from .forms import QuillFormField


class QuillField(models.TextField):

    def formfield(self, **kwargs):
        kwargs.update({"form_class": QuillFormField})
        return super().formfield(**kwargs)