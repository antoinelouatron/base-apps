"""
date: 2024-04-03

No django model here.
"""
import dataclasses
import datetime
import json
import logging

from agenda.models import compatibility, attendance
import agenda.models as am

logger = logging.getLogger(__name__)


class SortError(TypeError):
    """Custom exception for errors in sorted list"""

class SortedList(list):
    """Ascending sorted lists"""

    def insert(self, o):
        """Inserts a new element in correct position.

        Returns the insertion index i such as self[i] == o.
        The resulting SortedList is guaranteed to be as sorted as before...
        """
        n = len(self)
        if n == 0:
            super().append(o)
            return 0
        # classic dichotomic research
        m = 0
        mil = n // 2
        while m < n:
            if self[mil] < o:
                m = mil + 1
            elif self[mil] > o:
                n = mil - 1
            else:
                super().insert(mil, o)
                return mil
            mil = (n + m) // 2
        if m >= len(self):
            super().append(o)
            return len(self) - 1
        if self[m] < o:
            super().insert(m + 1, o)
            return m + 1
        super().insert(m, o)
        return m

    def insert_index(self, o):
        """Finds index for o in this SortedList.

        Useful to check for duplicates before using insert_at
        """
        n = len(self)
        if n == 0:
            return 0
        # classic dichotomic research
        m = 0
        mil = n >> 1
        while m < n:
            if self[mil] < o:
                m = mil + 1
            elif self[mil] > o:
                n = mil - 1
            else:
                return mil
            mil = (n + m) // 2
        if m >= len(self):
            return len(self)
        if self[m] < o:
            return m + 1
        return m

    def insert_at(self, i, o):
        """Insert at given position

        Be careful to keep this SortedList sorted.
        Returns self
        """
        if (i > 0 and self[i - 1] > o) or (i < len(self) and self[i] < o):
            raise SortError
        super().insert(i, o)
        return self

    def append(self, o):
        """
        Similar to list.append except a SortError will be raised if sort is broken.
        """
        if len(self) == 0:
            return super().append(o)
        if o < self[-1]:
            raise SortError()
        return super().append(o)

    def extend(self, slist):
        """
        Similar to list.extend except a SortError will be raised if sort is broken.

        slist must be an instance of SortedList
        """
        if not isinstance(slist, SortedList):
            raise SortError()
        if len(slist) > 0:
            if len(self) == 0 or slist[0] >= self[-1]:
                super().extend(slist)
            else:
                raise SortError()

    def reverse(self):
        """
        Not supported.
        """
        raise SortError()

class AgendaDay(SortedList):
    """Simple wrapper around SortedList

    Contain only TimeSpan objects. Filter empty spans in __iter__.
    """

    def __init__(self, num):
        super().__init__()
        self.label = am.PeriodicEvent.days_label[num]
        self.num = num
    
    def __iter__(self):
        for o in super().__iter__():
            if o.length == 0:
                continue
            yield o


class CompatTimetable():
    """
    No display, only construct an agenda responsible for checking the compatibility
    of each added events.

    Supported events : PeriodicEvent, CollePlanning, BaseEvent.

    Add events in this orders !
    """

    def __init__(self):
        self.periodics = [[] for d in range(6)] # monday->saturday
        self.events = []
        self.incomp = []
        compatible = True
    
    def add_periodic(self, pev: am.PeriodicEvent) -> compatibility.Compatibility:
        for e in self.periodics[pev.day]:
            c = e.compatible(pev)
            if not c:
                return c
        self.periodics[pev.day].append(pev)
        return compatibility.COMPATIBLE
    
    def add_colleplanning(self, cp: am.CollePlanning) -> compatibility.Compatibility:
        day = cp.event.day
        for e in self.periodics[day]:
            c = cp.compatible(e)
            if not c:
                return c
        self.periodics[day].append(cp)
        return compatibility.COMPATIBLE
    
    def add_baseevent(self, ev: am.BaseEvent) -> compatibility.Compatibility:
        if ev.override:
            self.events.append(ev)
            return compatibility.COMPATIBLE
        for day in self.periodics:
            for pev in day:
                c = ev.compatible(pev)
                if not c:
                    return c
        for bev in self.events:
            c = ev.compatible(bev)
            if not c:
                return c
        self.events.append(ev)
        return compatibility.COMPATIBLE
    
    @classmethod
    def construct(cls, pevs, cps, bevs):
        inst = cls()
        for pev in pevs:
            c = inst.add_periodic(pev)
            if not c:
                inst.incomp.append(c)
        for cp in cps:
            c = inst.add_colleplanning(cp)
            if not c:
                inst.incomp.append(c)
        for ev in bevs:
            c = inst.add_baseevent(ev)
            if not c:
                inst.incomp.append(c)
        inst.compatible = (len(inst.incomp) == 0)
        return inst

class DisplayAgenda():

    def __init__(self, evs=tuple()):
        self.days = [AgendaDay(d) for d in range(6)]
        self.add_evs(evs)
    
    def __iter__(self):
        for day in self.days:
            yield day
    
    def get_hours(self):
        """
        Compute a suitable set of times to display.

        Returns (hours, (min, max), time_span)
        where hours is a sorted list of time for begin or end,
        (min, max) the extremities and time_span a number of hours
        """
        L = []
        for h in range(am.MIN_HOUR.hour, am.MAX_HOUR.hour):
            L.append(datetime.time(h))
            L.append(datetime.time(h, 30))
        L.append(datetime.time(am.MAX_HOUR.hour))
        return L
    
    def to_context(self) -> dict:
        """
        Returns a dict suitable to add to context to render this timetable
        """
        return {
            "agenda": self,
            "hours": self.get_hours(),
            "bounds": (am.MIN_HOUR, am.MAX_HOUR),
        }

class DisplayTimeTable(DisplayAgenda):
    """
    No compatibility check.
    Contains days of TimeSpan's, each subsequently added in override mode.
    """
    
    def add_ev(self, ev: am.ToSpanMixin) -> None:
        span = ev.to_span()
        self.add_span(span)
    
    def add_base_ev(self, ev: am.BaseEvent) -> None:
        for span in ev.to_span():
            self.add_span(span)
    
    def add_evs(self, evs) -> None:
        for ev in evs:
            self.add_ev(ev)
    
    def add_span(self, span: am.TimeSpan) -> None:
        daynum = span.day
        day = self.days[daynum]
        index = day.insert(span)
        # first, preceding event.
        # We sort by beghour, at most one preceding event can be impacted
        if index > 0 and day[index - 1].endhour >= span.beghour:
            # we can't have a complete overlap, since we insert before
            # when 2 elements compare as equal.
            # incomplete overlap, shrink previous event
            day[index - 1].endhour = span.beghour
        # next overlaping events
        while index + 1 < len(day) and day[index + 1].beghour < span.endhour:
            if day[index + 1].endhour <= span.endhour:
                del day[index + 1]
            else:
                day[index + 1].beghour = span.endhour
    
    def get_current_day(self, day: datetime.date, week: am.Week) -> int:
        """
        Returns the index of the current day in this DisplayTimeTable.

        If day is not in week, returns 0 (monday) or 4.
        """
        if day in week:
            return min(day.weekday(), 4)
        if day < week.begin:
            return 0
        return 4 # friday, last displayed day

PARITY = ("paire", "impaire")
LETTERS = tuple("CAB") # week 1 is A
FOUR_LETTERS = tuple("DABC") # week 1 is A

@dataclasses.dataclass
class EventOccurences():
    begweek: int
    endweek: int
    groups: str # compact attendance string
    periodicity: int
    id: int

    def __str__(self):
        groups = self.groups
        if self.periodicity == 1:
            return groups
        return f"{PARITY[self.begweek % 2]} {groups}"

@dataclasses.dataclass
class MergeableSpan(compatibility.SpanComparisonMixin):
    """
    PeriodicEvent time span for timetable construction.

    We can have similar events we want to merge (group rotation for same
    timespan, only weeks/groups change)
    """
    beghour: datetime.time
    endhour: datetime.time
    day: int
    periodicity: int
    occurences: list[EventOccurences] # length 1 in creation
    ev: am.PeriodicEvent
    teachers: set[str] = dataclasses.field(default_factory=set)
    label: str = ""
    classroom: str = ""
    position: int = 0
    overlap_nb: int = 1
    subject: str = ""
    subj: str = ""
    
    @classmethod
    def from_ev(cls, pev: am.PeriodicEvent) -> "MergeableSpan":
        kwargs = pev.base_span_kwargs()
        att = am.attendance_kwargs(pev)
        occ = EventOccurences(
            begweek=pev.begweek,
            endweek=pev.endweek,
            groups=attendance.grouper.minify_groups(att["groups"]),
            periodicity=pev.periodicity,
            id=pev.id
        )
        return cls(
            occurences=[occ],
            teachers=att["teachers"],
            periodicity=pev.periodicity,
            ev=pev,
            label=pev.full_label,
            subj=pev.subj.pk if pev.subj else "",
            **kwargs)

    def is_similar(self, other: "MergeableSpan") -> bool:
        """
        Tests whether 2 spans represent the same event for different weeks/attendance.
        """
        return (
            self.beghour == other.beghour and
            self.endhour == other.endhour and
            self.periodicity == other.periodicity and
            self.label == other.label and
            self.teachers == other.teachers
            )

    def merge(self, other: "MergeableSpan") -> None:
        self.occurences.extend(other.occurences)
    
    def attendances(self) -> list[str]:
        """
        Returns a suitable label for attendance display (by colle group).
        """
        n = len(self.occurences)
        if self.periodicity == 1 or n > 4 or self.periodicity > 4:
            return []
        if self.periodicity == 2:
            labels = PARITY
        elif self.periodicity == 4:
            labels = FOUR_LETTERS
        else:
            labels = LETTERS
        grouped = {}
        for occ in self.occurences:
            label = labels[occ.begweek % self.periodicity]
            grouped.setdefault(occ.groups, []).append(label)
        lines = []
        for k, v in grouped.items():
            v.sort()
            lines.append(f"{', '.join(v)}: {k}")
        # for occ in self.occurences:
        #     lines.append(
        #         labels[occ.begweek % self.periodicity] + ": " + occ.groups)
        lines.sort()
        return lines
    
    def to_json(self):
        base = dataclasses.asdict(self)
        # use json for occurences since JSON require double quotes
        # and python outputs single quotes by default. (in dict_to_data)
        base["occurences"] = json.dumps(base["occurences"])
        base["teachers"] = json.dumps(base["teachers"])
        return base

class PeriodicConstruction(DisplayAgenda):
    
    def add_evs(self, evs):
        for ev in evs:
            self.add_ev(ev)
    
    def add_ev(self, ev: am.PeriodicEvent):
        ms = MergeableSpan.from_ev(ev)
        day = self.days[ms.day]
        index = day.insert_index(ms)
        # check previous and next events to find similarities
        i = min(index, len(day) - 1)
        while i >= 0 and day[i].beghour == ms.beghour:
            if ms.is_similar(day[i]):
                day[i].merge(ms)
                # at most one is similar
                return
            i -= 1
        # no need to check next events, we insert before in SortedList
        # i = index
        # while i < len(day):
        #     if ms.is_similar(day[i]):
        #         day[i].merge(ms)
        #         # at most one is similar
        #         return
        #     i += 1
        day.insert_at(index, ms)
    
    def update_overlaps(self):
        """
        Set position and overlap_nb all all contained MergeableSpan
        """
        for day in self:
            n = len(day)
            i = 0
            while i < n:
                # find how many consecutive events overlap.
                # day is sorted by beghour.
                j = i + 1 # first dandidate
                cur_ends = [day[i].endhour] # endhour of current overlap
                # stream
                max_end = day[i].endhour # end of current overlap stream
                ov_nb = 1 # maximum simultaneously overlaping event 
                while j < n and day[j].beghour < max_end:
                    k = 0 # index of first non-overlaping event with day[j]
                    # among events in cur_ends.
                    while k < len(cur_ends) and day[j].beghour < cur_ends[k]:
                        k += 1 # cur_ends[k] overlaps with day[j]
                    if k == len(cur_ends): # all current events overlap
                        ov_nb += 1
                        cur_ends.append(day[j].endhour)
                    else: # k will be the position from left to right
                        # of day[j]
                        cur_ends[k] = day[j].endhour
                    # in any case, update max_end and set position
                    max_end = max(max_end, day[j].endhour)
                    day[j].position = k
                    j += 1
                for k in range(i, j):
                    day[k].overlap_nb = ov_nb
                # skip all initialized events
                i = j