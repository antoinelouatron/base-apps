"""
Created on Tue Jan 19 14:58:03 2016
"""

import abc
import datetime

from agenda.models import attendance

class Compatibility():
    """
    Object representing compatibility of 2 events, with associated error data.
    """

    def __init__(self, compatible, ev1=None, ev2=None, user=None, time=None):
        if not compatible and (ev1 is None or ev2 is None or user is None):
            raise ValueError("Information manquante")
        self.ev1 = ev1
        self.ev2 = ev2
        self.user = user
        self.compatible = compatible
        if (ev1 is not None and ev2 is not None and 
                ev1.pk is not None and ev1.pk == ev2.pk and type(ev1) == type(ev2)):
            self.compatible = True
        self.time = time

    def __bool__(self):
        return self.compatible

    def __str__(self):
        if self.compatible:
            return "True"
        template = "%s participe à %s et %s"
        if self.time is not None:
            template += " à la date %s" % str(self.time)
        return template % (str(self.user), str(self.ev1), str(self.ev2))

COMPATIBLE = Compatibility(True)


class EventCompatibility():
    """Abstract class for event compatibility and attendance.

    Don't use externally.
    """

    @abc.abstractmethod
    def time_compatible(self, other):
        """
        Check wether two events of same type have disjoint time spans
        """

    @abc.abstractmethod
    def compatible_other(self, other):
        """
        Check whether two events of different types have disjoint time spans
        """

    # @cached_property
    @property
    def attendance_list(self) -> set:
        if hasattr(self, "_att"):
            return self._att
        att = set(attendance.grouper.to_list(self.attendance_string))
        self._att = att
        return att

    def compatible(self, other, att=None, **kwargs):
        """Checks if self and other can occur at same time with at least one common attendant.
        if att is not None, it overrides other.attendants or periodic event attendance in case
        of cross comparison

        """
        actual_att = att
        if att is None:
            actual_att = other.attendance_list

        if type(self) == type(other):
            tc = self.time_compatible(other, **kwargs)
        else:
            tc = self.compatible_other(other, **kwargs)
        if not tc:
            if isinstance(tc, Compatibility):
                return self._attendance_compatible(actual_att, other, tc)
            return self._attendance_compatible(actual_att, other)
        else:
            return COMPATIBLE

    def _attendance_compatible(self, att2, other, tc=Compatibility(True)):
        """
        Returns a boolean indicating whether this sets intersect (True for disjoint)
        """
        att1 = self.attendance_list
        inter = att1.intersection(att2)
        if inter:
            user = inter.pop()
            return Compatibility(False, self, other, user=user, time=tc.time)

        return COMPATIBLE


class SpanComparisonMixin():
    """
    Comparison of TimeSpan based on day then beghour.
    """
    beghour: datetime.time
    endhour: datetime.time

    @property
    def length(self):
        """
        Return the length of the event in minutes
        """
        delta = datetime.timedelta(
            hours=self.endhour.hour - self.beghour.hour,
            minutes=self.endhour.minute - self.beghour.minute
        )
        return delta.total_seconds() // 60

    def __lt__(self, other: "SpanComparisonMixin") -> bool:
        return self.day < other.day or (self.day == other.day and self.beghour < other.beghour)

    def __gt__(self, other: "SpanComparisonMixin") -> bool:
        return self.day > other.day or (self.day == other.day and self.beghour > other.beghour)

    def __le__(self, other: "SpanComparisonMixin") -> bool:
        return self.day < other.day or (self.day == other.day and self.beghour <= other.beghour)

    def __ge__(self, other: "SpanComparisonMixin") -> bool:
        return self.day > other.day or (self.day == other.day and self.beghour >= other.beghour)

    def __eq__(self, other: "SpanComparisonMixin") -> bool:
        return hasattr(self, "pk") and hasattr(other, "pk") and self.pk == other.pk
    
    def __hash__(self):
        return hash(self.pk)

    def overlap(self, other: "SpanComparisonMixin") -> bool:
        return ((self.beghour <= other.beghour < self.endhour) or
                (other.beghour <= self.beghour < other.endhour))
