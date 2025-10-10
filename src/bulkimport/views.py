"""
date: 2015-10-16
"""

from django import urls
from django.contrib import messages
import django.views.generic as views

from bulkimport import importers
from utils.views import TemplateView, FormView, UserIsStaffMixin

class ImportIndex(UserIsStaffMixin, TemplateView):

    template_name = "bulkimport/index.html"
    PAGE_TITLE = "Importer par JSON ou CSV"
    STYLES = []
    SCRIPTS = ["home"]
    
    def get_all_menus(self, context):
        account = self.account_menu_items()
        account.mark_current("import")
        return [account]

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["urls"] = importers.get_urls()
        return ctx

import_view = ImportIndex.as_view()

class ModelImportView(UserIsStaffMixin, FormView):
    """
    Base abstract view for importing data via FileImportForm.
    Use with form_class pointing to a child of FileImportForm

    Concrete class must have :
    model_name attribute : used to create the url pointing to self : "import:import_{model_name}"
    title_name: to display as href content
    
    To redirect after successful import, override get_sucess_url.
    Defaults to import index page.
    """

    template_name = "bulkimport/import.html"
    model_name = None
    title_name = ""
    STYLES = []
    SCRIPTS = ["home"]
    
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["action_url"] = urls.reverse(self.view_name)
        ctx["page_title"] = "Création de " + self.title_name
        ctx["model_name"] = self.title_name
        return ctx
    
    @property
    def view_name(self) -> str:
        return f"import:{self.model_name}"
    
    def get_all_menus(self, context):
        account = self.account_menu_items()
        account.mark_current("import")
        return [account]
    
    def form_valid(self, form):
        instances = form.save()
        messages.add_message(self.request, messages.INFO, f"{len(instances)} créé(s)")
        return super().form_valid(form)

    def get_success_url(self) -> str:
        return urls.reverse("import:index")

    @classmethod
    def register(cls, name):
        """
        Register to importfile index page.
        """
        view_name = f"{cls.model_name}"
        importers.register(view_name, name, cls)
