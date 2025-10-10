"""
date: 2024-02-24
"""
import datetime
import logging
from django.conf import settings
from django.db import models, transaction
import icalendar
import requests

logger = logging.getLogger(__name__)

class WeekQs(models.QuerySet):

    def for_today(self):
        today = datetime.date.today()
        return self.get(active=True, begin__lte=today, end__gte=today)
    
    def active(self):
        return self.filter(active=True)

class Week(models.Model):
    """
    Weeks in a school year, used to organize agenda.
    """

    class Meta:
        unique_together = ("begin", "end")
        verbose_name = "Semaine"
        ordering = ["begin"]
    
    begin = models.DateField(verbose_name="Premier jour")
    end = models.DateField(verbose_name="Dernier jour")
    # holiday/special weeks
    label = models.CharField(max_length=96, blank=True, default="")
    nb = models.IntegerField(null=True, db_index=True)
    active = models.BooleanField(default=False, verbose_name="Année courante")

    objects = WeekQs.as_manager()

    def adjacents(self):
        """
        Return previous and next week,if any, in a dict
        {'prev': week, 'next': week}
        """
        adj = {}
        prev = Week.objects.filter(end__lte=self.begin).order_by("-end")[:1]
        next_week = Week.objects.filter(begin__gte=self.end).order_by("begin")[:1]
        try:
            adj["prev"] = prev[0]
        except:
            pass
        try:
            adj["next"] = next_week[0]
        except:
            pass
        return adj

    def __str__(self):
        s = self.begin.strftime("%d/%m/%y") + " - " + self.end.strftime("%d/%m/%y")
        if self.label != "":
            s += " " + self.label
        elif self.nb is not None:
            s = "{}, {}".format(self.nb, s)
        return s
    
    def short_name(self):
        s = self.begin.strftime("%d/%m") + " - " + self.end.strftime("%d/%m")
        if self.nb is not None:
            s = "{}, {}".format(self.nb, s)
        return s
    
    def __contains__(self, obj):
        if isinstance(obj, datetime.datetime):
            date = obj.date()
        elif isinstance(obj, datetime.date):
            date = obj
        else:
            raise ValueError("Unable to compare {} to date objects".format(obj))
        return self.begin <= date <= self.end


class Holidays():
    
    def __init__(self):
        self._periods = []
    
    def __contains__(self, date):
        for v in self._periods:
            if v["begin"] <= date <= v["end"]:
                return True
        return False
    
    def get(self, date):
        for v in self._periods:
            if v["begin"] <= date <= v["end"]:
                return v["label"]
        return False
    
    def append(self, val):
        self._periods.append(val)
    
    def __len__(self):
        return len(self._periods)

class HolidayGenerator():
    """
    Responsible for generating Week objects according to one .ics file
    or between two datetime.date objects.

    Generated weeks begin on mondays and end on sundays
    """
    

    def __init__(self):
        self.loaded = False
        self.parsed = False
        self.load_ics()
        self.holidays = Holidays()
        self.parse_holidays()
    
    def download_open_data(self, out_path):
        req = requests.get(settings.AGENDA_OFFICIAL_ICAL_URL)
        if req.status_code == 200:
            with open(out_path, "w") as f:
                f.write(req.text)
                return True
        return False

    def load_ics(self):
        path = settings.AGENDA_ICAL_FILE
        if not path.exists():
            dl = self.download_open_data(path)
            if not dl:
                logger.error("No ICAL file found in url %s", settings.AGENDA_OFFICIAL_ICAL_URL)
                return
        with open(path) as f:
            try:
                self.calendar = icalendar.Calendar.from_ical(f.read())
                self.loaded = True
                return
            except:
                logger.error("Corrupted ICAL file found in url %s", settings.AGENDA_OFFICIAL_ICAL_URL)
        path.unlink(missing_ok=True)
    
    def parse_holidays(self):
        if self.parsed or not self.loaded:
            return
        for ev in self.calendar.walk("vevent"):
            label = str(ev.get("SUMMARY", ""))
            begin = ev.get("dtstart", None)
            end = ev.get("dtend", None) 
            if begin is not None and end is not None:
                begin = begin.dt
                end = end.dt - datetime.timedelta(1)
                self.holidays.append({"label": label, "begin": begin, "end": end})
            self.parsed = True
    
    def generate_between(self, start_day, end_day, active=False) -> list[Week]:
        """
        Generate new Week instances between 2 given dates.

        Be aware that (begin, end) is a unique key on this model.
        """
        b = start_day + datetime.timedelta(-start_day.weekday())
        seven_days = datetime.timedelta(7)
        e = b + datetime.timedelta(6)
        i = 0
        res = []
        with transaction.atomic():
            while b < end_day:
                label = self.holidays.get(b)
                if not label:
                    i += 1
                    res.append(Week(begin=b, end=e, nb=i, active=active))
                else:
                    res.append(Week(begin=b, end=e, label=label, active=active))
                e += seven_days
                b += seven_days
            Week.objects.bulk_create(res)
        return res
        
    
        