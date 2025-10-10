"""
date: 2024-04-11
"""
import datetime
from typing import Any
from django import forms, template, urls
from django.contrib import messages
from django.http import JsonResponse

import agenda.forms as af
import agenda.models as am
import agenda.views.home as ah
from agenda.models import timetable
from bulkimport import views as bv
from utils import reverse
import utils.views
from utils.views import mixins
import users.models as um


class BasePeriodicManage(mixins.UserIsStaffMixin,
    mixins.JSONFormMixin, utils.views.CreateUpdateView):
    """
    Create or update AbstractPeriodic events.
    We use formsets instead of forms.

    GET is done as usual, but POST responses are responses to AJAX requests
    """
    form_class = None
    model = None

    def create_agenda(self,pop_saturday=True):
        tt = timetable.PeriodicConstruction(self.get_queryset())
        if pop_saturday:
            tt.days.pop() # exclude saturday
        return tt
    
    def get_form_class(self):
        fset = forms.modelformset_factory(
            self.model,
            form=self.form_class,
            **self.get_formset_kwargs()
        )
        return fset

    def get_formset_kwargs(self):
        """
        kwargs passed to the formset factory
        """
        return {"extra": 0}
    
    def get_form_kwargs(self):
        """
        kwargs passed to the formset class
        """
        kwargs = super().get_form_kwargs()
        # create and update views are not meant for formset
        if "instance" in kwargs:
            kwargs.pop("instance")
        kwargs["prefix"] = "periodic"
        if not self.ajax:
            kwargs["queryset"] = self.model.objects.none()
        return kwargs
    
    def serialize_object(self, instances: list) -> dict:
        return [inst.to_json() for inst in instances]
    
    def final_data(self, serialization):
        tt = self.create_agenda()
        tmpl = template.loader.get_template(self.tt_render)
        return {
            "instances": serialization,
            "timetable": tmpl.render(tt.to_context())
        }
    
    def get_context_data(self, **kwargs: utils.views.Any) -> dict[str, Any]:
        ctx = super().get_context_data(**kwargs)
        tt = self.create_agenda()
        ctx.update(tt.to_context())
        ctx["empty_form"] = ctx["form"].empty_form
        ctx["tt_render"] = self.tt_render
        ctx["current_day"] = self.curr_day
        return ctx
    
    def get_level(self, level_id: str) -> um.Level:
        try:
            return um.Level.objects.get(pk=int(level_id))
        except:
            return um.get_default_level(instance=True)

    def post(self, request, *args, **kwargs):
        self.ajax = True
        self.level = self.get_level(kwargs.get("level_id", None))
        self.curr_day = request.POST.get("curr_day", 0)
        return super().post(request, *args, **kwargs)
    
    def get(self, request, *args, **kwargs):
        self.ajax = False
        self.level = self.get_level(kwargs.get("level_id", None))
        self.curr_day = 0
        return super().get(request, *args, **kwargs)

class CreateUpdatePeriodic(BasePeriodicManage):

    form_class = af.PeriodicForm
    model = am.PeriodicEvent
    template_name = "agenda/manage_periodics.html"
    form_template_name = "agenda/forms/periodic.html"
    tt_render = "agenda/timetable_construction.html"
    SCRIPTS = ["manage_agenda"]
    PAGE_TITLE = "Création de l'EDT"

    def get_queryset(self):
        qs =  am.PeriodicEvent.objects.order_by("day", "beghour", "subj")
        # TODO : filter by level after adding subject foreign key
        qs = qs.filter(subj__level=self.level)
        return qs

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["form_kwargs"] = { "filters": {
            "subj": {"level": self.level}
        }}
        return kwargs

    def get_all_menus(self, ctx):
        base = ah.agenda_menus()
        base.mark_current("calendar")
        account = self.account_menu_items()
        account.mark_current("agenda")
        return [account, base]

    def create_agenda(self, pop_saturday=True):
        ag = super().create_agenda(pop_saturday=pop_saturday)
        ag.update_overlaps()
        return ag
    
    def popns(self, **kwargs):
        ns = super().popns(**kwargs)
        groups = um.ColleGroup.objects.order_by("nb").values_list("nb", flat=True)
        teachers = um.User.objects.filter(teacher=True, is_active=True)
        ns["eventData"] = {
            "groups": list(groups),
            "letters": "ABC",
            "hournb": 11.5, # 8h-19h30
            "minhour": "08:00",
            "teachers": [t.display_name for t in teachers]
        }
        ns["urls"] = {
            "removePeriodic": urls.reverse("agenda:delete_periodic"),
        }
        return ns

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["level"] = self.level
        return ctx

class PrintTimetableView(CreateUpdatePeriodic):
    template_name = "agenda/printable_timetable.html"

class DeletePeriodicView(mixins.UserIsStaffMixin, mixins.BaseJsonView):
    model = am.PeriodicEvent

    def post(self, request, *args, **kwargs):
        try:
            pks = request.POST.get("ids", "")
            if pks != "":
                pks = [int(n) for n in pks.split(",")]
            else:
                pks = []
            self.model.objects.filter(pk__in=pks).delete()
            return self.ok({"deleted": len(pks)})
        except:
            return self.error("Erreur lors de la suppression")

class ImportTimetable(bv.ModelImportView):
    model_name = "edt"
    form_class = af.PeriodicImport
    title_name = "Emploi du temps"

ImportTimetable.register("Événements périodiques")

class ImportColleEvents(bv.ModelImportView):
    model_name = "colles"
    form_class = af.ColleEventImport
    title_name = "Colles"

ImportColleEvents.register("Créneaux de colle")

class ImportCollePlanning(bv.ModelImportView):
    model_name = "colloscope"
    form_class = af.CollePlanningImport
    title_name = "Planning de colles"

ImportCollePlanning.register("Planning de colles")

class ImportDsEvents(bv.ModelImportView):
    model_name = "ds"
    form_class = af.DsImport
    title_name = "Devoirs surveillés"

ImportDsEvents.register("Devoirs surveillés")

class ExportTimetable(mixins.UserIsTeacherMixin, mixins.BaseJsonView):
    
    def get_data(self, ctx):
        evs = am.PeriodicEvent.objects.filter(perso=False)
        ev_list = []
        for ev in evs:
            ev_list.append(ev.to_dict())
        return ev_list
    
    def get(self, request, *args, **kwargs):
        fname = "edt-PT-{date}.json".format(
            date=datetime.date.today().strftime("%d-%m-%y")
        )
        resp = JsonResponse(self.get_data({}), safe=False)
        resp["Content-Disposition"] = 'attachment; filename="{fname}"'.format(fname=fname)
        return resp

class TimetableDisplayMixin():

    def get_current_week(self):
        try:
            return am.Week.objects.for_today()
        except am.Week.DoesNotExist:
            return am.Week.objects.last()
    
    def base_urls(self):
        """
        URLs used in each timetable display view
        """
        if not self.request.user.is_authenticated:
            return {}
        return {
            "initialTt": reverse.without_trailing("agenda:user_timetable", week="0"),
            "weeksList": urls.reverse("agenda:api:week_api-list"),
            "usersList": urls.reverse("users:list"),
            "getMemo": reverse.without_trailing("agenda:note_detail", event="0", week="0"),
        }
    
    def base_ns(self, ns):
        ns["urls"] = self.base_urls()
        if self.week is not None:
            ns["week"] = self.week.pk
        return ns

class StandaloneTimetable(mixins.UserIsTeacherMixin, utils.views.TemplateView,
            TimetableDisplayMixin):
    
    template_name = "agenda/standalone_timetable.html"
    raise_exception = True
    SCRIPTS = ["standalone_tt"]
    PAGE_TITLE = "Gestion des mémos"

    def dispatch(self, request, *args, **kwargs):
        self.week = self.get_current_week()
        return super().dispatch(request, *args, **kwargs)

    def popns(self, **kwargs):
        return self.base_ns(super().popns(**kwargs))
    
    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        ctx = super().get_context_data(**kwargs)
        ctx["note_form"] = af.NoteForm()
        return ctx

class ToDoManageView(mixins.UserIsStaffMixin, utils.views.CreateUpdateView):
    model = am.ToDo
    form_class = af.ToDoForm
    template_name = "agenda/todo_form.html"
    PAGE_TITLE = "Création d'une tâche"
    SCRIPTS = ["home"]

    def get_all_menus(self, ctx):
        base = ah.agenda_menus()
        base.mark_current("todo")
        account = self.account_menu_items()
        account.mark_current("agenda")
        return [account, base]
    
    def get_success_url(self):
        messages.success(self.request, "Tâche ajoutée")
        return "/"

class ManageBaseEvent(mixins.UserIsStaffMixin,  TimetableDisplayMixin,
        utils.views.CreateUpdateView):
    model = am.BaseEvent
    form_class = af.BaseEventForm
    template_name = "agenda/base_event_form.html"
    PAGE_TITLE = "Création d'un événement"
    SCRIPTS = ["base_events"]

    def dispatch(self, request, *args, **kwargs):
        if "week" in request.GET:
            try:
                self.week = am.Week.objects.get(pk=request.GET["week"])
            except am.Week.DoesNotExist:
                self.week = am.Week.objects.last()
        else:
            self.week = self.get_current_week()
        return super().dispatch(request, *args, **kwargs)

    def get_all_menus(self, ctx):
        base = ah.agenda_menus()
        base.mark_current("events")
        account = self.account_menu_items()
        account.mark_current("agenda")
        return [account, base]
    
    def popns(self, **kwargs):
        ns = self.base_ns(super().popns(**kwargs))
        ns["urls.removeEvent"] = reverse.without_trailing_pk("agenda:delete_event")
        return ns
    
    def get_success_url(self):
        if self._edit_mode:
            messages.success(self.request, "Événement modifié")
        else:
            messages.success(self.request, "Événement ajouté")
        query_param = f"?week={self.object.week.pk}"
        return urls.reverse("agenda:manage_events") + query_param
    
    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        ctx = super().get_context_data(**kwargs)
        qs = am.BaseEvent.objects.order_by("begin").select_related("week")
        qs = qs.filter(inscriptionevent__isnull=True)
        ctx["events"] = qs
        ctx["week"] = self.week
        return ctx

class DeleteBaseEventView(mixins.UserIsStaffMixin, utils.views.DeleteView):
    model = am.BaseEvent
    success_url = urls.reverse_lazy("agenda:manage_events")
    http_method_names = ["post"]
    