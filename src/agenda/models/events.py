"""
Created on Tue Jan 19 14:59:17 2016
"""
import dataclasses
import datetime
import json
import functools
import math
import unidecode

from django.core.exceptions import ImproperlyConfigured
from django.db import models
from django.utils.timezone import get_default_timezone, make_aware, is_aware, localtime, now

from agenda import components
from agenda.models import Week
from agenda.models import compatibility, attendance
from users.models import User, Level, Subject, get_default_level

MIN_HOUR = datetime.time(8)
MAX_HOUR = datetime.time(19, 30)

def ensure_aware(dt):
    tz = get_default_timezone()
    return dt if is_aware(dt) else make_aware(dt, tz)

@dataclasses.dataclass
class TimeSpan(compatibility.SpanComparisonMixin):
    """
    Simple time representation to insert in a TimeTable.
    No compatibility check here
    """
    # absolute position in timetable
    beghour: datetime.time
    endhour: datetime.time
    day: int
    subject: str = ""
    label: str = ""
    type: str|None = None
    classroom: str = ""
    groups: str = "" # minified
    teachers: list = dataclasses.field(default_factory=list)
    note_nb: int = 0
    id: int = 0

    def __post_init__(self):
        self.pk = self.id

def attendance_kwargs(ev):
    groups = []
    teachers = []
    for el in ev.attendance_list:
        if isinstance(el, int):
            groups.append(el)
        else:
            teachers.append(el)
    groups.sort()
    return {
        "groups": groups,
        "teachers": teachers
    }


class AttendanceEvent(models.Model):

    class Meta:
        abstract = True
    
    attendants = models.ManyToManyField(User, verbose_name="Participants", blank=True)
    # do not use this field directly
    _attendance_string = models.TextField(verbose_name="Chaîne des participants",
        editable=False, blank=True, default="")
    # field manager. The managed field must have same name, prefixed by underscore
    attendance_string = attendance.AttendanceField()

class ToSpanMixin():

    def get_ref_event(self):
        return self
    
    def base_span_kwargs(self):
        ev = self.get_ref_event()
        return {
            "beghour": ev.beghour,
            "endhour": ev.endhour,
            "day": ev.day,
            "classroom": ev.classroom,
            "subject": ev.subj.name.lower() if ev.subj else ev.subject,
        }

    def get_span_kwargs(self) -> dict:
        kwargs = self.base_span_kwargs()
        kwargs.update(attendance_kwargs(self))
        return kwargs
    
    def to_span(self):
        return TimeSpan(**self.get_span_kwargs())

# TODO : remove that when link to subjects is complete.
# SUBJECTS = {
#     "math": "math",
#     "physique": "physique",
#     #"SII": "SII",
#     "francais": "français",
#     "anglais": "anglais",
#     "tipe": "TIPE",
#     "si": "SII",
#     "info": "info",
# }

class AbstractPeriodic(compatibility.SpanComparisonMixin, models.Model):
    """
    Common fields for Periodic ev and colle ev.
    All fileds can exists only in a Timetable, not in an Agenda (no date).
    """

    class Meta:
        abstract = True

    days_label = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi",
        "dimanche"]

    DAYS_CHOICES = list(zip(range(7), days_label))

    beghour = models.TimeField(verbose_name="Heure de début")
    endhour = models.TimeField(verbose_name="Heure de fin")
    day = models.PositiveSmallIntegerField(verbose_name="Jour de la semaine",
        choices=DAYS_CHOICES)
    # day of the week : 0..6
    subject = models.CharField(max_length=32, verbose_name="Matière", blank=True, default="")
    subj = models.ForeignKey(Subject, on_delete=models.CASCADE, null=True, default=None,
        verbose_name="Matière")
    classroom = models.CharField(max_length=10, verbose_name="Salle",
        blank=True, default="")

    @property
    def day_label(self):
        return self.days_label[self.day]

    def to_json(self):
        """
        Serialization to json object. Used in template (data attribute)
        and AJAX responses.
        """
        di = {
            "begweek": self.begweek,
            "endweek": self.endweek,
            "beghour": self.beghour.isoformat(),
            "endhour": self.endhour.isoformat(),
            "attendants": self.attendance_string,
            "day": self.day,
            "periodicity": self.periodicity,
            "label": self.label,
            "subject": self.subject,
            "id": self.id,
            "subj": self.subj.id if self.subj else "",
            }
        return json.dumps(di)

    def to_dict(self):
        """
        Used in timetable export and archive generation
        """
        return {
            "beghour": str(self.beghour),
            "endhour": str(self.endhour),
            "begweek": self.begweek,
            "endweek": self.endweek,
            "day": self.day,
            "periodicity": self.periodicity,
            "_attendance_string": self.attendance_string,
            "classroom": self.classroom,
            "subject": self.subject,
            "label": self.label,
        }

    @property
    def sep_subject(self):
        subj_label = self.subj.name if self.subj else self.subject
        sep = "d'" if subj_label.lower()[0] in "aeiou" else "de "
        return f"{sep}{subj_label}"

class PeriodicQuerySet(models.QuerySet):

    def for_week(self, week: Week):
        if week.nb is None:
            return self.none()
        qs = self.annotate(
            remainder=(week.nb - models.F("begweek")) % models.F("periodicity")
        )
        qs = qs.annotate(
            note_nb=models.Count("note", filter=models.Q(note__target_week=week))
        )
        return qs.filter(
            endweek__gte=week.nb,
            begweek__lte=week.nb,
            remainder=0
        )

class PeriodicEvent(
    compatibility.EventCompatibility, AbstractPeriodic, AttendanceEvent, ToSpanMixin
    ):
    """
    Represents an event occuring at regular interval of time
    """

    class Meta:
        verbose_name = "Evenement périodique"
        verbose_name_plural = "Evenements périodiques"

    begweek = models.IntegerField(verbose_name="Semaine de début")
    endweek = models.IntegerField(verbose_name="Semaine de fin")
    label = models.CharField(max_length=64, blank=True, verbose_name="Nom")
    periodicity = models.IntegerField(verbose_name="Périodicité")
    perso = models.BooleanField(default=False)

    objects = PeriodicQuerySet.as_manager()

    def time_compatible(self, other):
        """
        Check if two periodic events can overlap
        """
        if self.day != other.day:
            return True
        if (self.beghour <= other.beghour < self.endhour or
                other.beghour <= self.beghour < other.endhour):
            # check if there's a day intersection
            g = math.gcd(self.periodicity, other.periodicity)
            # b + up = b' + vp' iff b - b' = -up - vp' so gcd(p, p') | b - b'
            if (self.begweek - other.begweek) % g != 0:
                return True
            # current week to check
            a = self.begweek
            # make sure we start after other.begweek
            if a < other.begweek:
                a += ((other.begweek - a // self.periodicity) + 1) * self.periodicity
                # try all values for a
            while a <= self.endweek and (a - other.begweek) % other.periodicity != 0:
                a += self.periodicity
            if (a <= self.endweek and a <= other.endweek):
                # we found a common day
                return compatibility.Compatibility(
                    False, self, other, user=0,
                    time=" le {day} à {hour}".format(day=self.day, hour=self.beghour)
                )
            # else:
            return True
        else:
            return True

    def compatible_other(self, other):
        """
        Delegate to BaseEvent the responsibility to check for compatibility
        """
        return other.compatible_other(self)
    
    def occur_in_week(self, week: Week) -> bool:
        interval = (self.begweek <= week.nb <= self.endweek)
        return interval and not ((week.nb - self.begweek) % self.periodicity)

    def get_for_week(self, week: Week):
        """
        Returns a BaseEvent (an occurence) or None
        """
        if not self.occur_in_week(week):
            # not a week for this event
            return None
        curday = week.begin
        curday += datetime.timedelta(self.day)
        ev_beg = ensure_aware(datetime.datetime.combine(curday, self.beghour))
        ev_end = ensure_aware(datetime.datetime.combine(curday, self.endhour))
        return BaseEvent(begin=ev_beg, end=ev_end, week=week,
            _attendance_string=self.attendance_string,)

    def __str__(self):
        return f"{self.label} {self.day_label} {self.beghour}-{self.endhour}"

    @property
    def full_label(self):
        if self.label.endswith(self.sep_subject):
            return self.label
        return f"{self.label} {self.sep_subject}"

    def get_span_kwargs(self):
        kwargs = super().get_span_kwargs()
        kwargs["label"] = self.full_label
        kwargs["type"] = "periodic"
        kwargs["note_nb"] = getattr(self, "note_nb", 0)
        kwargs["id"] = self.id
        return kwargs

timeline_models = set()

class TimelineMetaclass(models.base.ModelBase):
    """
    Metaclass to register children classes for timeline display.
    This is used to display the event in a timeline.

    Use as metaclass for any model that should be displayed in a timeline.

    The class must define the attribute `timeline_template` with the path to the template
    to use for displaying the event in the timeline, and timeline_qs(cls, request) 
    classmethod
    to return the queryset of events to display in the timeline.
    """
    def __new__(cls, name, bases, attrs):
        newclass = super().__new__(cls, name, bases, attrs)
        if getattr(newclass, "timeline_template", None) is None:
            raise ImproperlyConfigured(
                "La classe {} doit définir l'attribut timeline_template.".format(newclass.__name__)  # analysis:ignore
            )
        if not hasattr(newclass, "timeline_qs"):
            raise ImproperlyConfigured(
                "La classe {} doit définir la méthode timeline_qs.".format(newclass.__name__)  # analysis:ignore
            )
        timeline_models.add(newclass)
        return newclass

class Note(models.Model, metaclass=TimelineMetaclass):
    """
    Simple notes attached to an occurrence of a PeriodicEvent. Used to display homework.
    """
    timeline_template = "agenda/timeline/note.html"

    target_week = models.ForeignKey(Week, on_delete=models.CASCADE)
    target_event = models.ForeignKey(PeriodicEvent, on_delete=models.CASCADE)
    comment = models.TextField()
    date = models.DateField(blank=True, null=True)

    def __str__(self):
        return "{}, semaine {}".format(self.target_event.label, self.target_week.nb)
    
    def save(self, *args, **kwargs):
        if self.date is None:
            self.date = self.target_week.begin
            self.date += datetime.timedelta(self.target_event.day)
        return super().save(*args, **kwargs)
    
    @classmethod
    def timeline_qs(cls, request):
        return Note.objects.filter(
            target_event__attendants=request.user,
            date__gte=datetime.date.today()
        ).order_by("date")

@functools.total_ordering
class BaseEvent(compatibility.EventCompatibility, AttendanceEvent):

    class Meta:
        verbose_name = "Evenement poncutel"
        verbose_name_plural = "Evenements ponctuels"

    begin = models.DateTimeField(verbose_name="Début")
    end = models.DateTimeField(verbose_name="Fin")
    label = models.CharField(max_length=64, blank=True, verbose_name="Nom")
    override = models.BooleanField(default=False,
        verbose_name="Prend le pas sur le reste")
    # make classroom part of common interface for all event types
    classroom = models.CharField(max_length=10, verbose_name="Salle",
        blank=True, default="")
    # we only allow event inside a week, enforced in save
    week = models.ForeignKey(Week, models.CASCADE,
        verbose_name="Semaine", null=True, blank=True, default=None,)
    
    def save(self, *args, **kwargs):
        if not self.week:
            self.week = self._find_week()
        super().save(*args, **kwargs)

    def _find_week(self):
        """
        Find the week for this event.
        If not found, raise ValueError
        """
        qs = Week.objects.filter(begin__lte=self.begin, end__gte=self.end)
        if qs.count() == 1:
            return qs[0]
        raise ValueError("No week for this event")

    def time_compatible(self, other):
        # incompatible iff one beginning is inside other event
        b = not ((self.begin <= other.begin < self.end) or
                 (other.begin <= self.begin < other.end))
        return b

    def __str__(self):
        if self.label != "":
            return "{} : {} - {}".format(self.label, self.begin, self.end)
        return str(self.begin) + " " + str(self.end)

    def __lt__(self, other):
        return self.begin < other.begin

    def __eq__(self, other):
        return self.pk == other.pk

    __hash__ = models.Model.__hash__

    def compatible_other(self, periodic_event: PeriodicEvent):
        """
        Test compatibility with a given periodic event.
        Only check times, not attendance
        """
        if self.override:
            return True
        occ = periodic_event.get_for_week(self.week)
        if occ is None:
            return True
        return self.time_compatible(occ)
        
    def _base_span(self, beghour, endhour, day, **kwargs):
        span_kwargs = {
            "beghour": beghour,
            "endhour": endhour,
            "day": day,
            "classroom": self.classroom,
            "subject": unidecode.unidecode(self.label.lower()),
            "label": self.label,
            "type": "base",
        }
        span_kwargs.update(attendance_kwargs(self))
        span_kwargs.update(**kwargs)
        span = TimeSpan(**span_kwargs)
        return span

    def _days(self):
        day = self.begin.date().weekday()
        yield day
        end_day = self.end.date().weekday()
        if self.end.date() > self.week.end:
            # truncate to one week
            end_day = 6
        day += 1
        while day <= end_day:
            yield day
            day += 1

    def to_span(self) -> list[TimeSpan]:
        """
        Returns a list of TimeSpan limited to one week, the Week
        containing self.begin
        """
        # more tricky : one event can span on multiple days.
        days = list(self._days())
        day_nb = len(days)
        beghour = localtime(self.begin).time()
        endhour = localtime(self.end).time()
        if day_nb == 1:
            span = self._base_span(beghour, endhour, days[0])
            return [span]
        spans = [
            self._base_span(beghour, MAX_HOUR, days[0])
        ]
        for i in range(1, day_nb - 1):
            spans.append(self._base_span(
                MIN_HOUR,
                MAX_HOUR,
                days[i]
            ))
        if endhour > MIN_HOUR:
            spans.append(self._base_span(
                MIN_HOUR,
                endhour,
                days[-1])
            )
        return spans

class ToDo(AttendanceEvent, metaclass=TimelineMetaclass):

    INFO = 0
    WARNING = 1
    ALERT = 2
    timeline_template = "agenda/timeline/todo.html"

    date = models.DateField(verbose_name="Jour")
    label = models.CharField(max_length=64, verbose_name="Nom")
    long_label = models.TextField(verbose_name="Description", blank=True, default="")
    msg_level = models.SmallIntegerField(default=0, verbose_name="Niveau de message",
        choices=((INFO, "Info"), (WARNING, "Avertissement"), (ALERT, "Alerte")))
    # TODO : add a reminder field with djangoq2 link ?

    def __str__(self):
        return self.label
    
    @classmethod
    def timeline_qs(cls, request):
        """
        Returns a queryset of ToDo for the current user.
        """
        return ToDo.objects.filter(attendants=request.user,
            date__gte=datetime.date.today()).order_by("date")

class InscriptionQuerySet(models.QuerySet):

    def open(self):
        return self.filter(begin__gt=make_aware(datetime.datetime.now()))

    def closed(self):
        return self.filter(begin__lte=make_aware(datetime.datetime.now()))
    
    def for_week(self, week: Week):
        """
        Returns all inscriptions for a given week
        """
        begin = make_aware(datetime.datetime.combine(week.begin, datetime.time(0)))
        end = make_aware(datetime.datetime.combine(week.end, datetime.time(23, 59)))
        return self.filter(
            begin__gte=begin,
            end__lte=end
        )
    
    def user_attend(self, user: User):
        """
        Returns all inscriptions for a given user
        """
        filt = models.Q(attendants=user) | models.Q(teacher=user)
        return self.filter(filt).distinct()

class InscriptionEvent(BaseEvent, metaclass=TimelineMetaclass):
    timeline_template = "agenda/timeline/inscription.html"

    max_students = models.PositiveSmallIntegerField(verbose_name="Nombre de places")
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Professeur")
    override = True
    is_full = models.BooleanField(default=False, verbose_name="Complet")
    week = True #bypass week management

    objects = InscriptionQuerySet.as_manager()

    def locked(self):
        """
        Lock for inscription one day before the beginning
        """
        td = datetime.timedelta(days=1)
        return self.begin < make_aware(datetime.datetime.now() + td)
    
    def as_widget(self):
        """
        For manage page
        """
        return components.InscriptionWidget(self)
    
    def past(self):
        return self.end < now()
    
    def to_span(self):
        return [self._base_span(
            beghour=localtime(self.begin).time(),
            endhour=localtime(self.end).time(),
            day=self.begin.date().weekday(),
            subject="inscription",
        )]
    
    @property
    def date(self):
        return self.begin.date()
    
    @classmethod
    def timeline_qs(cls, request):
        """
        Returns a queryset of InscriptionEvent for the current user.
        """
        return InscriptionEvent.objects.user_attend(request.user).filter(
            begin__gte=now()
        ).select_related("teacher").order_by("begin").distinct()

class InscriptionGroup():
    """
    Group of inscriptions for a given day/teacher
    """

    def __init__(self, day: datetime.date, teacher: User):
        self.day = day
        self.teacher = teacher
        self.inscriptions = {}

    def add_inscription(self, inscription: InscriptionEvent):
        label = inscription.label
        if label not in self.inscriptions:
            self.inscriptions[label] = []
        self.inscriptions[label].append(inscription)
    
    def as_widget(self):
        """
        For list page
        """
        return components.InscriptionGroupWidget(self)
