"""
date: 2024-04-15
"""
import datetime
import logging
from typing import Any

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
from django.views.generic.edit import CreateView

from rest_framework import viewsets, serializers
import rest_framework.authentication
from rest_framework.permissions import IsAuthenticated

import agenda.forms.events as aevents
from agenda.models import timetable, year, events, colles, utils
import users.models as um
from utils.views import mixins

logger = logging.getLogger(__name__)

class PersoTTView(LoginRequiredMixin, mixins.JSONTemplateView):

    template_name = "agenda/timetable_json.html"
    raise_exception = True # 403 instead of 302->/login

    def get(self, request, *args, week=None, user_id=None, **kwargs):
        try:
            self.week = year.Week.objects.get(pk=week)
            self.curr_user = request.user
            # spoofing !
            if (self.curr_user.teacher or self.curr_user.is_staff) and user_id is not None:
                self.curr_user = um.User.objects.get(pk=int(user_id))
            return super().get(request, *args, **kwargs)
        except ObjectDoesNotExist:
            logger.info("Week not found")
            return self.error("Semaine non trouvée")
        except Exception as e:
            logger.error("Problem !", exc_info=e)
            return self.error("Problème serveur")

    def get_periodics(self):
        qs = events.PeriodicEvent.objects.for_week(self.week)
        qs = qs.filter(attendants=self.curr_user)
        return qs
    
    def get_events(self):
        qs = events.BaseEvent.objects.select_related("week").filter(week=self.week)
        if self.curr_user.is_staff and "all" in self.request.GET:
            return qs
        qs = qs.filter(attendants=self.curr_user)
        return qs
    
    def get_colles(self):
        qs = colles.CollePlanning.objects.for_user(self.curr_user).filter(
            week=self.week).select_related("week")
        return qs
    
    def get_inscriptions(self):
        qs = events.InscriptionEvent.objects.for_week(self.week).open()
        qs = qs.user_attend(self.curr_user)
        return qs
    
    def construct_timetable(self):
        tt = timetable.DisplayTimeTable(self.get_periodics())
        tt.add_evs(self.get_colles())
        for bev in self.get_events():
            tt.add_base_ev(bev)
        for inscr in self.get_inscriptions():
            tt.add_base_ev(inscr)
        return tt
    
    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        ctx = super().get_context_data(**kwargs)
        ctx["event_render"] = "agenda/perso_tt_event.html"
        tt = self.construct_timetable()
        saturday = tt.days.pop()
        ctx.update(tt.to_context())
        ctx["agenda"] = tt
        ctx["saturday"] = saturday[:1]
        today = datetime.date.today()
        ctx["current_day"] = tt.get_current_day(today, self.week)
        ctx["week"] = self.week
        ctx["adjacent"] = self.week.adjacents()
        ctx["is_teacher"] = self.request.user.teacher
        ctx["curr_user"] = self.curr_user # for testing
        return ctx

class WeekSerializer(serializers.ModelSerializer):
    class Meta:
        model = year.Week
        fields = ["pk", "begin", "end", "nb", "label"]

class WeekViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = year.Week.objects.active()
    serializer_class = WeekSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [rest_framework.authentication.SessionAuthentication]

class TimelineView(LoginRequiredMixin, mixins.JSONTemplateView):
    template_name = "agenda/timeline_json.html"
    raise_exception = True
    
    def get_all(self):
        return utils.regroup_by_month(
            *[model.timeline_qs(self.request) for model in events.timeline_models]
        )

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        ctx = super().get_context_data(**kwargs)
        ctx["timeline"] = self.get_all()
        ctx["is_teacher"] = self.request.user.teacher
        ctx["curr_user"] = self.request.user
        return ctx

class NoteDetailView(LoginRequiredMixin, mixins.JSONTemplateView):
    """
    Retrieve all notes for  given event and week
    """
    template_name = "agenda/components/note_detail.html"
    raise_exception = True

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        ctx = super().get_context_data(**kwargs)
        self.notes = ctx["notes"] = events.Note.objects.filter(
            target_event=kwargs["event"],
            target_week=kwargs["week"]
        ).select_related("target_event", "target_week")
        return ctx
    
    def get_data(self, ctx):
        data = super().get_data(ctx)
        if len(self.notes) > 0:
            data["title"] = f"Pour le {self.notes[0].date.strftime('%d/%m/%Y')}"
        else:
            data["title"] = "Aucun mémo"
        return data

class CreateNoteView(mixins.UserIsTeacherMixin, mixins.JSONFormView, CreateView):
    model = events.Note
    form_class = aevents.NoteForm
    template_name = "agenda/forms/note_form.html"
    raise_exception = True

    def serialize_object(self, obj):
        return {
            "comment": obj.comment
        }

class CheckAgendaView(mixins.UserIsStaffMixin, mixins.JSONTemplateView):
    template_name = "agenda/check_agenda.html"
    raise_exception = True

    def construct_agenda(self):
        pevs = events.PeriodicEvent.objects.all()
        cps = colles.CollePlanning.objects.all()
        return timetable.CompatTimetable.construct(pevs, cps, [])
    
    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        ctx = super().get_context_data(**kwargs)
        ctx["agenda"] = self.construct_agenda()
        return ctx
