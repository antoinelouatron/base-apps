"""
date: 2024-06-12

ToDo and InscriptionEvent management.
"""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction, models

import agenda.forms.events as afe
import agenda.models as am
import agenda.models.events as ame
from agenda.views import events as ave
from utils.views import DetailView, mixins, CreateUpdateView, ListView, DeleteView
from utils import reverse, menu

class BaseStudentInscriptionView(LoginRequiredMixin, mixins.JSONTemplateView, DetailView):
    model = am.InscriptionEvent
    raise_exception = True
    http_method_names = ["post"]
    template_name = "agenda/inscription_detail.html"

    def get_queryset(self):
        qs = super().get_queryset().prefetch_related("attendants")
        return qs.select_for_update() # lock the row before we check count, for race condition
    

class StudentInscriptionView(BaseStudentInscriptionView):
    
    def post(self, request, *args, **kwargs):
        with transaction.atomic():
            self.object = self.get_object()
            att = self.object.attendants.all()
            if len(att) >= self.object.max_students:
                return self.error("Plus de place disponible.")
            if request.user in att:
                return self.error("Vous êtes déjà inscrit.")
        
            self.object.attendants.add(request.user)
            if len(att)+1 == self.object.max_students:
                self.object.is_full = True
                self.object.save()
            self.object.refresh_from_db()
            self.object.has_user = True # emulate annotation
            return self.ok({"inscr": self.object})

class CancelInscriptionView(BaseStudentInscriptionView):
    
    def post(self, request, *args, **kwargs):
        with transaction.atomic():
            self.object = self.get_object()
            att = self.object.attendants.all()
            if request.user not in att:
                return self.error("Vous n'êtes pas inscrit.")
            if self.object.locked():
                return self.error("Vous ne pouvez plus vous désinscrire. Trouvez un remplaçant.")
        
            self.object.attendants.remove(request.user)
            self.object.is_full = False
            self.object.save()
            self.object.refresh_from_db()
            return self.ok({"inscr": self.object})

def inscription_base_menu(request):
    ml = menu.MenuList(title="Inscriptions")
    mi = menu.MenuItem("Liste", name="list",
        url=reverse.reverse("agenda:inscription:list"))
    ml.append(mi)
    if request.user.teacher:
        mi = menu.MenuItem("Gérer", name="manage",
            url=reverse.reverse("agenda:inscription:manage"))
        ml.append(mi)
    return ml

# TODO : load same week timetable when creating a new inscription
class ManageInscriptionView(mixins.UserIsTeacherMixin, ave.TimetableDisplayMixin,
            CreateUpdateView):
    model = am.InscriptionEvent
    form_class = afe.InscriptionForm
    PAGE_TITLE = "Gestion des séances sur inscriptions"
    raise_exception = True
    template_name = "agenda/inscription_manage.html"
    SCRIPTS = ["inscription_manage"]
    
    def get_initial(self):
        # removed in form if we are editing an existing inscription, 
        # and current user.is_staff
        return {"teacher": self.request.user}

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["teacher"] = self.request.user
        return kwargs
    
    def get_current_week(self):
        if self._edit_mode:
            try:
                return am.Week.objects.get(
                    begin__lte=self.object.begin,
                    end__gte=self.object.end)
            except am.Week.DoesNotExist:
                return super().get_current_week()

    def get_context_data(self, **kwargs):
        self.week = self.get_current_week() # we need to set this before popns
        ctx = super().get_context_data(**kwargs)
        qs = am.InscriptionEvent.objects.order_by("-begin").prefetch_related("attendants")
        if not self.request.user.is_staff:
            qs = qs.filter(teacher=self.request.user)
        else:
            # we need to know if the current user is the concerned teacher
            # in widget template, which have no access to current request.
            for obj in qs:
                obj.curr_user = self.request.user
        ctx["inscriptions"] = qs
        ctx["week"] = self.week
        ctx["min_size"] = "none"
        return ctx
    
    def get_success_url(self):
        return self.request.path
    
    def get_all_menus(self, context):
        ml = inscription_base_menu(self.request)
        ml.mark_current("manage")
        return [ml]
    
    def get_breadcrumb(self, context):
        bd = super().get_breadcrumb(context)
        head = bd.pop()
        bd.append(menu.MenuItem("Inscriptions", url=reverse.reverse("agenda:inscription:list")))
        bd.append(head)
        return bd

    def check_edit_right(self, instance):
        """
        Check if the current user is the teacher of the inscription.
        """
        if self.request.user.is_staff:
            return True
        if instance.teacher != self.request.user:
            messages.error(self.request, "Vous ne pouvez pas modifier cette inscription.")
            return False
        return True
    
    def popns(self, **kwargs):
        ns = self.base_ns(super().popns(**kwargs))
        ns["urls.removeEvent"] = reverse.without_trailing_pk("agenda:delete_event")
        return ns
    
    def get(self, request, *args, **kwargs):
        self.get_object() # store result in self.object, set _edit_mode
        if self._edit_mode and not self.check_edit_right(self.object):
            self.object = None
            self._edit_mode = False
        return super().get(request, *args, **kwargs)
    
    def post(self, request, *args, **kwargs):
        self.get_object()
        if self._edit_mode and not self.check_edit_right(self.object):
            self.object = None
            self._edit_mode = False
            form = self.get_form()
            form.instance = am.InscriptionEvent()
            return super().form_invalid(form)
        return super().post(request, *args, **kwargs)

class InscriptionListView(LoginRequiredMixin, ListView):
    model = am.InscriptionEvent
    template_name = "agenda/inscription_list.html"
    PAGE_TITLE = "Créneaux disponibles sur inscription"
    SCRIPTS = ["inscriptions"]
    raise_exception = True

    def get_queryset(self):
        qs = am.InscriptionEvent.objects.open().order_by("begin", "teacher")
        qs = qs.prefetch_related("attendants")
        qs = qs.annotate(
            has_user=models.Count(
                "attendants", filter=models.Q(attendants=self.request.user)
            )
        )
        return qs.distinct()
    
    def _regroup_inscriptions(self, qs):
        """
        Regroup inscriptions by date and teacher.
        """
        grouped = {}
        for inscription in qs:
            date = inscription.begin.date()
            teacher = inscription.teacher
            if date not in grouped:
                grouped[date] = {}
            if teacher not in grouped[date]:
                grouped[date][teacher] = ame.InscriptionGroup(date, teacher)
            grouped[date][teacher].add_inscription(inscription)
        return grouped
    
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["inscriptions"] = self._regroup_inscriptions(ctx["object_list"])
        if not hasattr(self.request, "content_ctx") or not self.request.content_ctx.config.inscription:
            messages.info(
                self.request,
                "Les séances sur inscriptions ne sont pas encore ouvertes cette année."
            )
        return ctx
    
    def popns(self, **ctx):
        ns = super().popns(**ctx)
        ns["urls"] = {
            "add": reverse.without_trailing_pk("agenda:inscription:add"),
            "cancel": reverse.without_trailing_pk("agenda:inscription:cancel"),
            "seeAll": reverse.reverse("agenda:inscription:list_passed"),
        }
        return ns
    
    def get_all_menus(self, context):
        ml = inscription_base_menu(self.request)
        ml.mark_current("list")
        return [ml]

class PastInscriptionsListView(LoginRequiredMixin, mixins.JSONTemplateView):
    template_name = "agenda/inscription_list_past.html"
    raise_exception = True

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        qs = am.InscriptionEvent.objects.closed()
        ctx["inscriptions"] = qs.order_by("begin").prefetch_related("attendants")
        return ctx

class DeleteInscriptionView(mixins.UserIsTeacherMixin, DeleteView):
    model = am.InscriptionEvent
    PAGE_TITLE = "Supprimer une séance sur inscription"
    raise_exception = True
    template_name = "agenda/inscription_delete.html"
    http_method_names = ["get", "post"]
    SCRIPTS = ["home"]
    
    def get_success_url(self):
        return reverse.reverse("agenda:inscription:manage")
    
    def get_all_menus(self, context):
        ml = inscription_base_menu(self.request)
        mi = menu.MenuItem("Supprimer", name="delete",
            url=reverse.reverse("agenda:inscription:delete",kwargs={"pk": self.object.pk}))
        ml.append(mi)
        ml.mark_current("delete")
        return [ml]
    
    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        context = self.get_context_data(object=self.object, form=self.get_form())
        return self.render_to_response(context)