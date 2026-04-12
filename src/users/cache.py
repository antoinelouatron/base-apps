from typing import Iterable

import users.models as um

class _SubjectCache:
    """
    Ready-only cache for subjects
    Keys are subject pks, values are levels
    """
    def __init__(self):
        self._cache = {}
        self.stale = True

    def get(self, pk: str) -> um.Level|None:
        if self.stale:
            self._populate_cache()
        return self._cache.get(pk)

    def __getitem__(self, subj: um.Subject|str|int):
        if isinstance(subj, um.Subject):
            subj = str(subj.pk)
        if isinstance(subj, int):
            subj = str(subj)
        return self.get(subj)

    def _populate_cache(self):
        qs = um.Subject.objects.select_related("level").only("pk", "level")
        self._cache = {str(s.pk): s.level for s in qs}
        self.stale = False

subjects = _SubjectCache()

class _QsProxy():
    # prox .all method from queryset, wraps an iterable
    # Used as initial queryset for some forms (InscriptionForm)

    model = um.User

    def __init__(self, data: Iterable):
        self._data = data

    def all(self):
        return self
    
    def get(self, pk=None):
        for obj in self._data:
            if obj.pk == pk:
                return obj
        raise um.User.DoesNotExist
    
    def __iter__(self):
        yield from self._data
    
    # render optgroups
    _prefetch_related_lookups = False

    def iterator(self):
        return self


class _UserCache:
    """
    Ready-only cache for teachers/colleurs

    Keys are level instances, values are lists of users
    """
    def __init__(self, qs, role):
        self.qs = qs.all()
        self.role = role
        self._cache = {}
        self.stale = True

    def get(self, level: um.Level, as_qs=False) -> list[um.User]:
        if self.stale:
            self._populate_cache()
        if as_qs:
            return _QsProxy(self._cache.get(level, []))
        return self._cache.get(level, [])

    def __getitem__(self, level):
        return self.get(level)

    def _populate_cache(self):
        qs = self.qs.all()
        for u in qs:
            for k, v in u.roles[self.role].items():
                if v:
                    level = subjects[k] # could be None
                    self._cache[level] = self._cache.get(level, [])
                    self._cache[level].append(u)
        self.stale = False

class _StudentCache():
    """
    Fake cache, but sami API as _UserCache
    """

    def get(self, level: um.Level):
        return um.User.objects.students(level)

    def __getitem__(self, level: um.Level):
        return self.get(level)

teachers = _UserCache(
    um.User.objects.teachers().filter(is_active=True),
    um.AtomicRole.TEACHER
)

colleurs = _UserCache(
    um.User.objects.colleurs().filter(is_active=True),
    um.AtomicRole.COLLEUR
)

students = _StudentCache()