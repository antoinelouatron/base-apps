"""
date: 2026-01-18
"""

import abc
from typing import Any

import agenda.models as am
from . import colles as colle_model
import users.models as um
from utils.components import Component

# Wrappers pour l'affichage des objets dans les tableaux de colloscope.
# Chaque wrapper utilise un template spécifique.
# compact=True permet d'utiliser une version compacte du template.
class EventDisplayWrapper(Component):
    template_name = "agenda/components/cscope_event_display.html"

    def __init__(self, event: Any, compact=False):
        self.obj = event
        self.compact = compact
    
    def get_context_data(self) -> dict:
        ctx = super().get_context_data()
        ctx["obj"] = self.obj
        ctx["compact"] = self.compact
        return ctx

class GroupDisplayWrapper(EventDisplayWrapper):
    template_name = "agenda/components/cscope_group_display.html"
    
class WeekDisplayWrapper(EventDisplayWrapper):
    template_name = "agenda/components/cscope_week_display.html"

# constantes pour les types de données de cscope
WEEK = 0
EVENT = 10
GROUP = 100

class SeparatorRow():
    is_separator = True

    def __iter__(self):
        yield from []

class DisplayTable():
    converters = {
        WEEK: WeekDisplayWrapper,
        EVENT: EventDisplayWrapper,
        GROUP: GroupDisplayWrapper
    }

    def __init__(self, colnames=None, rownames=None, rowlabel=None,
                 collabel=None):
        self.col_names = colnames
        self.row_names = rownames
        self.row_label = rowlabel
        self.col_label = collabel
        self.data = []
        # default layout
        self.col_type = WEEK
        self.row_type = EVENT
        self.data_type = GROUP
        self.separators = set() # d'indices après lesquels ajouter une ligne de séparation
    
    def set_layout(self, row_type, col_type):
        if row_type not in self.converters:
            raise ValueError(f"Invalid row type: {row_type}")
        if col_type not in self.converters:
            raise ValueError(f"Invalid column type: {col_type}")
        if row_type == col_type:
            raise ValueError("Row type and column type must be different")
        self.row_type = row_type
        self.col_type = col_type
        self.data_type = next(dtype for dtype in self.converters if dtype not in (row_type, col_type))
    
    def set_data(self, data: list[list], compact=False):
        self.data = [[None for _ in self.col_names] for _ in self.row_names]
        data_converter = self.converters[self.data_type]
        for row_idx, row in enumerate(data):
            for col_idx, col in enumerate(row):
                self.data[row_idx][col_idx] = data_converter(col, compact=compact)
    
    def transpose(self):
        self.row_names, self.col_names = self.col_names, self.row_names
        self.row_label, self.col_label = self.col_label, self.row_label
        self.row_type, self.col_type = self.col_type, self.row_type
        self.data = [list(col) for col in zip(*self.data)]
    
    def rows(self):
        for i in range(len(self.data)):
            yield [self.row_names[i]] + self.data[i]
            if i in self.separators:
                yield SeparatorRow()


class DbScope(abc.ABC):

    def __init__(self, level: um.Level):
        self.week_filter = {}
        self.group_filter = {}
        self.event_filter = {}
        self.planning_filter = {}
        self.level = level
    
    def set_week_range(self, min_week: int=None, max_week: int = None):
        if min_week is not None:
            self.week_filter["nb__gte"] = min_week
        if max_week is not None:
            self.week_filter["nb__lte"] = max_week
        
    
    def set_group_range(self, min_group: int=None, max_group: int=None):
        if min_group is not None:
            self.group_filter["nb__gte"] = min_group
        if max_group is not None:
            self.group_filter["nb__lte"] = max_group
    
    def set_event_teacher(self, teacher: um.User):
        self.event_filter = {"teacher": teacher}
        self.planning_filter = {"event__teacher": teacher}
    
    def compute_week_range(self):
        mini = None
        maxi = None
        for planning in self.plannings:
            week_nb = planning.week.nb
            if mini is None or week_nb < mini:
                mini = week_nb
            if maxi is None or week_nb > maxi:
                maxi = week_nb
        self.set_week_range(min_week=mini, max_week=maxi)
    
    def fetch_data(self):
        self.events = colle_model.ColleEvent.objects.filter(
            subj__level=self.level, **self.event_filter).select_related(
                "subj", "teacher").order_by("subj", "day", "beghour")
        self.groups = colle_model.ColleGroup.objects.filter(
            level=self.level, **self.group_filter
            ).prefetch_related("studentcollegroup_set__user").order_by("nb")
        self.plannings = colle_model.CollePlanning.objects.filter(
            event__subj__level=self.level, **self.planning_filter).select_related(
                "event__teacher", "week", "group")
        if not self.week_filter:
            self.compute_week_range()
        self.weeks = colle_model.Week.objects.filter(
            nb__isnull=False, active=True, **self.week_filter).order_by("nb")
        
    
    @abc.abstractmethod
    def build_display_table(self, compact=False) -> DisplayTable:
        pass

class GroupDataTable(DbScope):
    """
    Colloscope complet : semaines en abscisses, créneaux en ordonnées
    """
    
    def build_display_table(self, compact=False) -> DisplayTable:
        self.fetch_data()
        columns = [week for week in self.weeks]
        rows = list(self.events)
        table = DisplayTable(
            colnames=[str(week.nb) + " " + week.begin.strftime("%d/%m") for week in columns],
            rownames=[EventDisplayWrapper([event]) for event in rows],
            rowlabel="Créneaux",
            collabel="Semaines"
        )
        table.set_layout(row_type=EVENT, col_type=WEEK)
        data = []
        week_nb_to_idx = {week.nb: idx for idx, week in enumerate(columns)}
        event_to_idx = {event: idx for idx, event in enumerate(rows)}
        data = [["" for _ in columns] for _ in rows]
        for planning in self.plannings:
            week_nb = planning.week.nb
            if planning.event not in event_to_idx or week_nb not in week_nb_to_idx:
                continue
            row_idx = event_to_idx[planning.event]
            col_idx = week_nb_to_idx[week_nb]
            data[row_idx][col_idx] = planning.group
        table.set_data(data, compact=compact)
        # séparer les matières par une ligne de séparation
        last_subj = None
        for row_idx, event in enumerate(rows):
            if last_subj is None:
                last_subj = event.subj
            elif event.subj != last_subj:
                table.separators.add(row_idx - 1)
                last_subj = event.subj
        return table

class EventDataTable(DbScope):
    """
    planning pour un ou des groupes : semaines en ordonnées, groupes en abscisses
    """
    
    def build_display_table(self, compact=False) -> DisplayTable:
        self.fetch_data()
        columns = [group for group in self.groups]
        rows = [week for week in self.weeks]
        table = DisplayTable(
            colnames=[f"Gr. {group.nb}" for group in columns],
            rownames=[week.nb for week in rows],
            rowlabel="Semaine",
            collabel="Groupe"
        )
        table.set_layout(row_type=WEEK, col_type=GROUP)
        data = []
        group_nb_to_idx = {group.nb: idx for idx, group in enumerate(columns)}
        week_nb_to_idx = {week.nb: idx for idx, week in enumerate(rows)}
        data = [[[] for _ in columns] for _ in rows]
        for planning in self.plannings:
            if planning.group.nb not in group_nb_to_idx:
                continue
            week_nb = planning.week.nb
            row_idx = week_nb_to_idx[week_nb]
            col_idx = group_nb_to_idx[planning.group.nb]
            data[row_idx][col_idx].append(planning.event)
        table.set_data(data, compact=compact)
        return table

class CompatMatrix():
    """
    Compatibility (symetric) matrix for a set of events
    """
    table : dict[int, dict[int, bool]]

    def __init__(self, events=None):
        if events is not None:
            self.set_events(events)

    def set(self, ev1, ev2):
        "Sets 2 elements of this matrix"
        compat = ev1.time_compatible(ev2)
        self.table[ev1.id][ev2.id] = compat
        self.table[ev2.id][ev1.id] = compat
        return self

    def get(self, ev1, ev2):
        return self.table[ev1.id].get(ev2.id)

    def set_events(self, events):
        "Replace current content with compatibilites for given events"
        self.table = {ev.id: {} for ev in events}
        for ev1 in events:
            for ev2 in events:
                if self.get(ev1, ev2) is None:
                    self.set(ev1, ev2)
        return self

    def to_nsdata(self):
        return {
            k: {k2: "true" if v2 else "false" for (k2, v2) in v.items()} for (k, v) in self.table.items()
        }

class CompatByWeek():
    # TODO : test this !
    def __init__(self, level, colle_events, periodic_events, weeks):
        self.level = level
        self.colle_events = colle_events
        self.periodic_events = periodic_events
        self.weeks = weeks
        self.compat_by_week = {}
        self.group_nbs = um.ColleGroup.objects.filter(
            level=level, nb__isnull=False).order_by("nb").values_list("nb", flat=True)
        self.compute_compatibilities()
    
    def _for_event(self, event: am.ColleEvent, intersecting_events: list[am.PeriodicEvent]) -> CompatMatrix:
        compat_table = {}
        for week in self.weeks:
            free_groups = set(self.group_nbs)
            for pevent in intersecting_events:
                if pevent.occur_in_week(week):
                    for group in pevent.attendance_list:
                        if group in free_groups:
                            free_groups.remove(group)
            compat_table[week.nb] = list(free_groups)
        return compat_table

    def compute_compatibilities(self):
        for event in self.colle_events:
            intersect = []
            for pevent in self.periodic_events:
                if not event.time_compatible(pevent):
                    intersect.append(pevent)
            self.compat_by_week[event.id] = self._for_event(event, intersect)
                
