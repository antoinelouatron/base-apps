"""
date: 2026-01-18
"""
from django.views.generic.detail import SingleObjectMixin

import agenda.forms.cscope as cscope_forms
import agenda.models.cscope as cscope
import users.models as um
from utils.views import FormView, TemplateView

class ConsultCscopeView(SingleObjectMixin, FormView):
    """
    Vue appelée par HTMX, retourne le colloscope suivant les paramètres passés
    dans le formulaire.
    """
    model = um.Level
    form_class = cscope_forms.CscopeFilterForm
    template_name = "agenda/htmx/consult_cscope.html"
    PAGE_TITLE = "Consultation du colloscope"

    def get(self, request, *args, **kwargs):
        self.object = self.level = self.get_object()
        form = self.get_form()
        self.params = {}
        if not form.is_valid():
            return self.form_invalid(form)
        self.params = form.cleaned_data
        return super().get(request, *args, **kwargs)
    
    def get_form_kwargs(self):
        return {
            "data": self.request.GET or None,
        }
    
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["level"] = self.level
        group_table = cscope.GroupDataTable(self.level)
        min_week = self.params.get("min_week", None)
        max_week = self.params.get("max_week", None)
        group_table.set_week_range(min_week=min_week, max_week=max_week)
        display_table = group_table.build_display_table(compact=True)
        ctx["table"] = display_table
        return ctx

class PersoCscopeView(ConsultCscopeView):
    """
    Vue appelée par HTMX, retourne le colloscope personnel de l'utilisateur
    connecté.
    """
    template_name = "agenda/htmx/perso_cscope.html"
    PAGE_TITLE = "Mon colloscope"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["prefix"] = "perso"
        return kwargs
    
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["level"] = self.level
        min_week = self.params.get("min_week", None)
        max_week = self.params.get("max_week", None)
        if self.request.user.roles.is_student(level=self.level):
            event_table = cscope.EventDataTable(self.level)
            event_table.set_week_range(min_week=min_week, max_week=max_week)
            groups = um.StudentColleGroup.objects.select_related("group").filter(user=self.request.user)
            for cg in groups:
                cg = cg.group
                event_table.set_group_range(min_group=cg.nb, max_group=cg.nb)
            display_table = event_table.build_display_table()
        elif self.request.user.roles.is_colleur():
            event_table = cscope.GroupDataTable(self.level)
            event_table.set_week_range(min_week=min_week, max_week=max_week)
            event_table.set_event_teacher(self.request.user)
            display_table = event_table.build_display_table(compact=True)
        else:
            raise PermissionError("Utilisateur non autorisé à consulter un colloscope personnel.")
        
        ctx["table"] = display_table
        return ctx

class CscopeOverview(SingleObjectMixin, TemplateView):
    """
    Vue principale, charge les précédentes via HTMX
    """
    model = um.Level
    template_name = "agenda/cscope_overview.html"
    PAGE_TITLE = "Aperçu du colloscope"
    SCRIPTS = ["home"]

    def get(self, request, *args, **kwargs):
        self.object = self.level = self.get_object()
        return super().get(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["level"] = self.level
        ctx["form"] = cscope_forms.CscopeFilterForm()
        ctx["perso_form"] = cscope_forms.CscopeFilterForm(prefix="perso")
        return ctx