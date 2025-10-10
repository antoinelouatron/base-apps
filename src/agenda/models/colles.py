"""
Created on Tue Jan 19 15:03:09 2016
"""

import datetime

from django.db import models

from users.models import User, ColleGroup, get_default_level, Level
from agenda.models import Week, events, compatibility


class ColleEventManager(models.Manager):

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.select_related("teacher")


class ColleEvent(events.AbstractPeriodic):

    class Meta:
        verbose_name = "Créneau de colle"
        verbose_name_plural = "Créneaux de colles"

    teacher = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Professeur")
    order = models.PositiveSmallIntegerField(default=0)
    # level = models.ForeignKey(Level, on_delete=models.CASCADE, verbose_name="Classe",
    #     default=get_default_level)
    # acts as a hidden foreign key to link CollePlanning to ColleEvent
    # when importing
    abbrev = models.CharField(max_length=10, blank=True, default="")
    periodicity = 1

    objects = ColleEventManager()

    def __str__(self):
        return (self.teacher.display_name + " " +
                self.day_label +
                " " + str(self.beghour)[:-3] + "-" + str(self.endhour)[:-3])
    
    @property
    def attendance_list(self):
        return [self.teacher.display_name]
    
    @property
    def full_label(self):
        return f"Colle {self.sep_subject}"
    
    @property
    def attendance_string(self):
        return self.teacher.display_name

    def short_name(self):
        return "{} {}-{}".format(
            self.day_label,
            str(self.beghour)[:-3],
            str(self.endhour)[:-3]
        )

    def time_compatible(self, other):
        if self.day != other.day:
            return True
        return not self.overlap(other)


class CPManager(models.Manager):

    def get_queryset(self) -> models.QuerySet:
        return super().get_queryset().select_related(
            "event__teacher", "week", "group")

    def for_user(self, user):
        """
        Returns events concerning given YearUser.

        Beware of using this on the manager, and not on the queryset.
        """
        qs = self.get_queryset()
        if user.is_authenticated and user.teacher:
            return qs.filter(event__teacher=user)
        if user.is_authenticated:
            return qs.filter(
                group__nb__in=user.studentcollegroup.values_list(
                    "group__nb", flat=True))
        return self.none()

class CollePlanning(models.Model, compatibility.EventCompatibility, events.ToSpanMixin,
            metaclass=events.TimelineMetaclass):
    """
    Main colloscope data to store.
    """

    class Meta:
        verbose_name = "Colle"
        unique_together = ("event", "week")
    
    timeline_template = "agenda/timeline/colle.html"

    event = models.ForeignKey(ColleEvent, on_delete=models.CASCADE,
        verbose_name="Créneau")
    week = models.ForeignKey(Week, models.CASCADE, verbose_name="Semaine")
    group = models.ForeignKey(
        ColleGroup, # TODO : double reference to level here. Should we check consistency ?
        models.CASCADE,
        verbose_name="Groupe",
        null=True,
        default=None
    )
    postponed = models.BooleanField(default=False, verbose_name="Reportée")

    objects = CPManager()

    @property
    def colle_group(self):
        return self.group.nb

    def __str__(self):
        return "groupe %i, semaine %i, %s" % (self.group.nb, self.week.nb or -1,
            self.event)
    
    @property
    def attendance_string(self):
        return f"{self.colle_group},{self.event.teacher.display_name}"
    
    @property
    def attendance_list(self):
        return set((self.colle_group, self.event.teacher.display_name))
    
    @property
    def date(self):
        return self.week.begin + datetime.timedelta(self.event.day)
    
    def get_ref_event(self):
        return self.event

    def base_span_kwargs(self):
        kwargs = super().base_span_kwargs()
        if self.group.void:
            label = "Groupe vide !"
        else:
            label = self.event.full_label
        kwargs["label"] = label
        kwargs["type"] = "colle"
        return kwargs
    
    def time_compatible(self, other):
        return self.week!= other.week or self.event.time_compatible(other.event)
    
    def compatible_other(self, other):
        if isinstance(other, events.PeriodicEvent):
            return (not other.occur_in_week(self.week)) or self.event.time_compatible(other)
        # compare to BaseEvent. Delegate to other the comparison,
        # but we have to implement get_for_week
        return other.compatible_other(self)
    
    def get_for_week(self, week):
        if week != self.week:
            return None
        day = self.week.begin + datetime.timedelta(self.event.day)
        ev_beg = events.ensure_aware(
            datetime.datetime.combine(day, self.event.beghour))
        ev_end = events.ensure_aware(
            datetime.datetime.combine(day, self.event.endhour))
        return events.BaseEvent(begin=ev_beg, end=ev_end, week=week)
    
    @classmethod
    def timeline_qs(cls, request):
        return CollePlanning.objects.for_user(request.user).select_related(
            "week", "event").filter(
                week__begin__gte=datetime.date.today()
            ).order_by("week__begin", "event__day")[:5]
