"""
date: 2025-07-19
"""

from django.db import models
from django.db.models.functions import Lower

from .modelfields import DescriptionListField, SubGradesField

class Level(models.Model):

    class Meta:
        verbose_name = "Classe"
        verbose_name_plural = "Classes"
        ordering = ("first_year", "name")
        constraints = [
            models.UniqueConstraint(
                Lower("name"),name="unique_lower_name_level",
            )
        ]

    name = models.CharField(max_length=32, verbose_name="Classe")
    first_year = models.BooleanField(default=False, verbose_name="Première année")
    student_count = models.IntegerField(default=0, verbose_name="Nombre d'élèves")
    # Ce nombre est celui validé pour les VS, pas forcément celui du nombres
    # d'élèves encore actif à l'instant T.

    def ORS(self) -> int:
        """
        Returns the ORS (Obligation Réglementaire de Service) for this level.
        """
        if self.first_year:
            if self.student_count < 20:
                return 11
            if self.student_count < 35:
                return 10
            return 9
        if self.student_count < 20:
            return 10
        if self.student_count < 35:
            return 9
        return 8
    
    def __str__(self):
        return self.name

def get_default_level(instance=False) -> Level|int:
    obj, _ = Level.objects.get_or_create(name="PT")
    if instance:
        return obj
    return obj.pk

class AddDataTemplate(models.Model):
    """
    A template for additional data to provide, beside a numeric grade, 
    for a colle grade.
    """
    # This should live in colles/models/add_data.py, but we need it here for the
    # ForeignKey in Subject.
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, default="")
    owner = models.ForeignKey("users.User", on_delete=models.SET_NULL,
        null=True, blank=True, verbose_name="Créateur")
    skills = DescriptionListField(verbose_name="Compétences", blank=True)
    # list of {name: str, description: str?}

    skill_grades = DescriptionListField(verbose_name="Échelle de notes",
        blank=True)
    # list of {name: str, description: str?}

    sub_grades = SubGradesField(verbose_name="Notes intermédiaires", blank=True)
    # dict of {subgrade_name: max_grade}

    skills_by_week = models.JSONField(default=dict,
        verbose_name="Compétences par semaine", blank=True)
    # dict of {week_number: [skill_name, ...]}. Keys are strings.

    locked = models.BooleanField(default=False,
        verbose_name="Verrouillé",
        editable=False,
    )

    class Meta:
        verbose_name = "Modèle de données supplémentaires"
        verbose_name_plural = "Modèles de données supplémentaires"
        ordering = ("name",)
        constraints = [
            models.UniqueConstraint(
                Lower("name"),name="unique_lower_name_adddatatemplate",
            )
        ]

    def __str__(self):
        return self.name

    def get_skills_for_week(self, week: int|str) -> list[dict]:
        """
        Returns the list of skills to evaluate for the given week number.
        """
        # try int key then str key, if self is not fetched from db
        if week not in self.skills_by_week:
            week = str(week)
            if week not in self.skills_by_week:
                return self.skills
        skill_names = set()
        names = set(self.skills_by_week[week])
        skills = []
        for skill in self.skills:
            if skill["name"] in names and skill["name"] not in skill_names:
                skills.append(skill)
                skill_names.add(skill["name"])
        return skills

    def can_edit(self, user) -> bool:
        """
        Returns True if the given user can edit this template.
        """
        return user.is_superuser or (
            self.owner is not None and self.owner == user
        )
    
    def delete(self, *args, **kwargs):
        if self.locked:
            raise ValueError("Ce modèle de données est verrouillé et ne peut pas être supprimé.")
        return super().delete(*args, **kwargs)

class Subject(models.Model):
    """
    Represents a subject taught in a level.
    """
    class Meta:
        verbose_name = "Matière"
        verbose_name_plural = "Matières"
        ordering = ("level", "name",)
        unique_together = (("name", "level"),)

    name = models.CharField(max_length=32, verbose_name="Matière")
    level = models.ForeignKey(Level, on_delete=models.CASCADE, verbose_name="Classe")
    data_template = models.ForeignKey(AddDataTemplate, on_delete=models.SET_NULL,
        null=True, blank=True, verbose_name="Données de colle")

    def __str__(self):
        return self.name
    
    def full_name(self):
        return f"{self.name} {self.level.name}"

def prepare_qs_for_component(queryset):
    return {str(obj.pk): obj for obj in queryset}

class AtomicRole():
    NONE = "n"
    STUDENT = "s" # need level
    TEACHER = "t" # need subject and level
    COLLEUR = "c" # need subject and level
    SECRETARY = "sec" # no additional data needed
    SCHOOL_ADMIN = "sa" # no additional data needed
    REF_TEACHER = "rt" # need level, referent teacher for the level

    _NEED_LEVEL = {STUDENT, REF_TEACHER}
    _NEED_SUBJECT = {TEACHER, COLLEUR}
    _PROTECTED = {SECRETARY, SCHOOL_ADMIN} # can't delete this role, unless by superuser
    _TRANSLATIONS = {
        NONE: "Aucun",
        STUDENT: "Élève",
        TEACHER: "Enseignant",
        COLLEUR: "Colleur",
        SECRETARY: "Secrétaire",
        SCHOOL_ADMIN: "Administration",
        REF_TEACHER: "Prof référent",
    }

    def __init__(self, role=NONE, level=None, subject=None):
        """
        level and subject are optional pks.
        """
        if role in AtomicRole._NEED_LEVEL and level is None:
            raise ValueError("Une classe est requise pour le rôle {}".format(
                AtomicRole._TRANSLATIONS[role]))
        if role in AtomicRole._NEED_SUBJECT and subject is None:
            raise ValueError("Une matière est requise pour le rôle {}".format(
                AtomicRole._TRANSLATIONS[role]))
        if role not in AtomicRole._TRANSLATIONS:
            raise ValueError("Rôle inconnu {}".format(role))
        self.role = role
        if level is not None:
            self.level = str(level)
        else:
            self.level = None
        if subject is not None:
            self.subject = str(subject)
        else:
            self.subject = None

    def to_dict(self):
        d = {
            "role": self.role,
        }
        if self.level:
            d["level"] = self.level
        if self.subject:
            d["subject"] = self.subject
        return d

    def __eq__(self, other):
        if not isinstance(other, AtomicRole):
            return False
        return (self.role == other.role and
                self.level == other.level and
                self.subject == other.subject)

    def __repr__(self):
        return f"AtomicRole(role='{self.role}', level={self.level}, subject={self.subject})"

    @classmethod
    def create(cls, student=False, teacher=False, colleur=False, secretary=False,
            school_admin=False, ref_teacher=False, level=None, subject=None):
        """
        Create an AtomicRole instance based on the provided parameters.
        """
        if isinstance(level, Level):
            level = level.pk
        if isinstance(subject, Subject):
            subject = subject.pk
        if student:
            return cls(role=cls.STUDENT, level=level)
        if teacher:
            return cls(role=cls.TEACHER, level=level, subject=subject)
        if colleur:
            return cls(role=cls.COLLEUR, level=level, subject=subject)
        if secretary:
            return cls(role=cls.SECRETARY)
        if school_admin:
            return cls(role=cls.SCHOOL_ADMIN)
        if ref_teacher:
            return cls(role=cls.REF_TEACHER, level=level)
        return cls(role=cls.NONE)

class Roles():

    def __init__(self):
        self.reset()

    def reset(self):
        """
        Reset the roles to an empty state.
        """
        self.roles = {
            AtomicRole.SECRETARY: False,
            AtomicRole.SCHOOL_ADMIN: False,
            AtomicRole.STUDENT: {},
            AtomicRole.TEACHER: {},
            AtomicRole.COLLEUR: {},
            AtomicRole.REF_TEACHER: None, # ou pk de Level
        }
    
    def _cached_property(self, name, qs, atomic_role):
        if not hasattr(self, f"_{name}_cache"):
            cache = []
            for obj in qs:
                pk = str(obj.pk)
                if pk in self[atomic_role] and self[atomic_role][pk]:
                    cache.append(obj)
            setattr(self, f"_{name}_cache", cache)
        return getattr(self, f"_{name}_cache")

    @property
    def teacher_subjects(self):
        return self._cached_property(
            "teacher_subjects",
            Subject.objects.select_related("level", "data_template"),
            AtomicRole.TEACHER
        )
    
    @property
    def colleur_subjects(self):
        return self._cached_property(
            "colleur_subjects",
            Subject.objects.select_related("level"),
            AtomicRole.COLLEUR
        )

    @property
    def student_levels(self):
        return self._cached_property(
            "student_levels",
            Level.objects.all(),
            AtomicRole.STUDENT
        )

    @property
    def teacher_levels(self):
        levels = set()
        for subject in self.teacher_subjects:
            levels.add(subject.level)
        return list(levels)

    def __getitem__(self, role: str):
        """
        Get the role by its name.
        """
        if role in self.roles:
            return self.roles[role]
        raise KeyError("Role inconnu.")
    
    def __iter__(self):
        if self.roles[AtomicRole.SECRETARY]:
            yield AtomicRole.create(secretary=True)
        if self.roles[AtomicRole.SCHOOL_ADMIN]:
            yield AtomicRole.create(school_admin=True)
        if self.roles[AtomicRole.REF_TEACHER] is not None:
            yield AtomicRole.create(
                ref_teacher=True,
                level=self.roles[AtomicRole.REF_TEACHER]
            )
        for level in self.roles[AtomicRole.STUDENT]:
            if self.roles[AtomicRole.STUDENT][level]:
                yield AtomicRole.create(
                    student=True,
                    level=level
                )
        for subject in self.roles[AtomicRole.TEACHER]:
            if self.roles[AtomicRole.TEACHER][subject]:
                yield AtomicRole.create(
                    teacher=True,
                    subject=subject
                )

    def add(self, role: AtomicRole):
        """
        Add a new role to the user.
        """
        if role.role == AtomicRole.SECRETARY:
            self.roles[AtomicRole.SECRETARY] = True
        elif role.role == AtomicRole.SCHOOL_ADMIN:
            self.roles[AtomicRole.SCHOOL_ADMIN] = True
        elif role.role in (AtomicRole.TEACHER, AtomicRole.COLLEUR):
            self.roles[role.role][role.subject] = True
        elif role.role == AtomicRole.STUDENT:
            self.roles[AtomicRole.STUDENT][role.level] = True
        elif role.role == AtomicRole.REF_TEACHER:
            self.roles[AtomicRole.REF_TEACHER] = role.level
    
    def remove(self, role: AtomicRole):
        """
        Remove a role from the user.
        """
        if role.role == AtomicRole.SECRETARY:
            self.roles[AtomicRole.SECRETARY] = False
        elif role.role == AtomicRole.SCHOOL_ADMIN:
            self.roles[AtomicRole.SCHOOL_ADMIN] = False
        elif role.role in (AtomicRole.TEACHER, AtomicRole.COLLEUR):
            if str(role.subject) in self.roles[role.role]:
                del self.roles[role.role][str(role.subject)]
        elif role.role == AtomicRole.STUDENT:
            if str(role.level) in self.roles[AtomicRole.STUDENT]:
                del self.roles[AtomicRole.STUDENT][str(role.level)]
        elif role.role == AtomicRole.REF_TEACHER:
            if self.roles[AtomicRole.REF_TEACHER] == str(role.level):
                self.roles[AtomicRole.REF_TEACHER] = None
    
    def update(self, roles_dict: dict):
        """
        Update roles from a dict with same keys as AtomicRole.to_dict().
        """
        for k in self.roles:
            if k in roles_dict:
                self.roles[k] = roles_dict[k]
        return self

    def set(self, roles: list[AtomicRole]):
        """
        Set roles for the user, replacing existing ones.
        """
        self.reset()
        for role in roles:
            self.add(role)
        
    def to_json(self):
        return self.roles
    
    def is_admin(self) -> bool:
        """
        Returns True if the user has school admin role.
        """
        return self.roles[AtomicRole.SCHOOL_ADMIN]
    
    def is_secretary(self) -> bool:
        """
        Returns True if the user has secretary role.
        """
        return self.roles[AtomicRole.SECRETARY]
    
    def _check_role(self, obj, obj_type, key) -> bool:
        # same tests for all dict based roles.
        if obj is None:
            return bool(self.roles[key])
        if isinstance(obj, obj_type):
            obj = obj.pk
        obj = str(obj)
        return obj in self.roles[key] and self.roles[key][obj]
    
    def is_student(self, level:Level|int=None) -> bool:
        """
        Returns True if the user has student role for the given level.
        """
        return self._check_role(level, Level, AtomicRole.STUDENT)

    def is_teacher(self, subject:Subject|int=None, level=None) -> bool:
        """
        Returns True if the user has teacher role for the given subject.
        """
        return self._check_role(subject, Subject, AtomicRole.TEACHER)

    def is_colleur(self, subject:Subject|int=None, level=None) -> bool:
        """
        Returns True if the user has colleur role for the given subject.
        """
        return self._check_role(subject, Subject, AtomicRole.COLLEUR)

    def is_ref_teacher(self, level:Level|int=None) -> bool:
        """
        Returns True if the user is a referent teacher for the given level
        or for any level if no level is given
        """
        if level is None:
            return self.roles[AtomicRole.REF_TEACHER] is not None
        if isinstance(level, Level):
            level = level.pk
        return self.roles[AtomicRole.REF_TEACHER] == str(level)
    
    def display_data(self, levels: dict[str, Level],
            subjects: dict[str, Subject]) -> list[dict]:
        """
        Returns a list of strings representing the roles for display.
        """
        roles = []
        for role in self:
            r = AtomicRole._TRANSLATIONS.get(role.role, "Inconnu")
            if role.subject is not None:
                subject = subjects.get(role.subject)
                if subject:
                    subject_label = str(subject)
                    if subject_label[0].lower() in "aeiou":
                        prepo = "d'"
                    else:
                        prepo = "de "
                    r += f" {prepo}{subject_label}"
                    role.level = str(subject.level.pk)
            if role.level is not None:
                level = levels.get(role.level)
                if level:
                    level_label = str(level)
                    prepo = "en "
                    r += f" {prepo}{level_label}"
            roles.append({
                "role": r,
                "protected": role.role in AtomicRole._PROTECTED,
                "data": role.to_dict()
            })
        return roles

class RolesField(models.JSONField):
    """
    Custom field to store roles as a list of dicts.
    """
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("default", Roles)
        super().__init__(*args, **kwargs)

    def from_db_value(self, value, expression, connection):
        if value is None:
            return Roles()
        value = super().from_db_value(value, expression, connection)
        instance = Roles().update(value)
        return instance

    def get_prep_value(self, value):
        if isinstance(value, Roles):
            return value.to_json()
        return super().get_prep_value(value)
    
    def validate(self, value, model_instance):
        return isinstance(value, Roles)