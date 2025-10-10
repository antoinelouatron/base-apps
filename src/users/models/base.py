"""
See roles.py for structuring models (Level, Subject, ...)
"""

import bisect
import random
import string

from django.contrib.auth.models import AbstractUser, UserManager, AnonymousUser
from django.contrib.postgres.indexes import GinIndex
from django.db import models
from django.utils import text
from django.utils.translation import gettext_lazy as _

from . import roles as umr

def _randstring(n=8):
    random.seed()
    chars = string.ascii_lowercase
    return "".join(random.choice(chars) for _ in range(n))

def get_username(first_name="", last_name="", **kwargs):
    """
    default username : last_name[:8] + first_name[0].
    add letters of first_name if user already exists.

    returns a unique username.
    """
    fname = text.slugify(first_name)
    lname = text.slugify(last_name)
    usernames = [u["username"] for u in User.objects.all().values("username").order_by('username')]
    usernb = len(usernames)
    n = min(len(lname) + 1, 8)
    # first try
    for i in range(1, n):
        uname = lname[:(n - i)] + fname[:i]
        index = bisect.bisect_left(usernames, uname)
        if index >= usernb or usernames[index] != uname:
            return uname
    # random username as fallback
    uname = _randstring()
    index = bisect.bisect_left(usernames, uname)
    while index < usernb and usernames[index] == uname:
        uname = _randstring()
        index = bisect.bisect_left(usernames, uname)
    return uname

class MyUserManager(UserManager):

    def create(self, username=None, **kwargs):
        if username is None:
            if "last_name" not in kwargs or "first_name" not in kwargs:
                raise ValueError("No username nor first/last name provided")
            username = get_username(**kwargs)
        return super().create_user(username, **kwargs)
    
    def create_teacher(self, subject=None, **kwargs):
        kwargs["teacher"] = True
        inst = self.create(**kwargs)
        if subject is not None:
            inst.roles.add(umr.AtomicRole.create(teacher=True, subject=subject))
            inst.save()
        return inst

    def create_student(self, colle_group=None, level=None, **kwargs):
        kwargs["student"] = True
        inst = self.create(**kwargs)
        if colle_group is not None:
            if level is None:
                group_obj = ColleGroup.objects.get_or_create(nb=colle_group, void=False)[0]
            else:
                group_obj = ColleGroup.objects.get_or_create(nb=colle_group,
                    level=level, void=False)[0]
                inst.roles.add(umr.AtomicRole.create(student=True, level=level))
                inst.save()
            StudentColleGroup.objects.create(
                group=group_obj,
                user=inst
            )
        return inst
    
    def level(self, level: umr.Level):
        """
        Return a queryset of users in the given level.
        """
        filter = models.Q(roles__s__contains={level.pk: True})
        for subject in umr.Subject.objects.filter(level=level):
            filter |= models.Q(roles__t__contains={subject.pk: True})
            filter |= models.Q(roles__c__contains={subject.pk: True})
        return self.filter(filter).order_by("roles", "last_name", "first_name")

    def students(self, level: umr.Level):
        """
        Return a queryset of students in the given level.
        """
        return self.filter(roles__s__contains={level.pk: True})

    def teachers(self, subject: umr.Subject):
        """
        Return a queryset of teachers for the given subject.
        """
        return self.filter(roles__t__contains={subject.pk: True})
    
    def secretaries(self):
        """
        Return a queryset of secretaries.
        """
        return self.filter(roles__sec=True)
    
    def school_admins(self):
        """
        Return a queryset of school admins.
        """
        return self.filter(roles__sa=True)
    
    def colleurs(self, subject: umr.Subject):
        """
        Return a queryset of colleurs for the given subject.
        """
        return self.filter(roles__c__contains={str(subject.pk): True})

class User(AbstractUser):
    # type hint
    roles: umr.Roles
    
    class Meta:
        verbose_name = "Utilisateur"
        verbose_name_plural = "Utilisateurs"
        ordering = ("last_name", "first_name",)
        indexes = [GinIndex(fields=["roles"]), models.Index(fields=["username"])]

    MONSIEUR = "M."
    MADAME = "Mme."
    MX = "Mx."
    # override blank=True
    email = models.EmailField(_("adresse email"), blank=False)
    title = models.CharField(
        max_length=4,
        choices={
            MONSIEUR: "Monsieur",
            MADAME: "Madame",
            MX: "Mx",
        },
        blank=True, default="",
        verbose_name=_("Civilité"),
    )
    # included fields : username, first_name, last_name, email, password
    # groups, user_permissions, is_staff, is_active, is_superuser, last_login, date_joined
    roles = umr.RolesField(verbose_name="Rôles", blank=True)
    # legacy role management, for content app
    teacher = models.BooleanField(default=False) # PT/math-info
    student = models.BooleanField(default=False)
    
    objects = MyUserManager()

    def save(self, *args, **kwargs):
        if self.username is None or self.username == "":
            self.username = get_username(first_name=self.first_name, last_name=self.last_name)
        super().save(*args, **kwargs)
    
    def get_full_name(self) -> str:
        if self.title:
            params = (self.title, self.last_name)
        else:
            params = (self.last_name, self.first_name)
        return "{} {}".format(*params).strip()
    
    @property
    def display_name(self):
        return self.get_full_name()
    
    # for compatibility with colle grade forms
    @property
    def short_name(self):
        return f"{self.last_name} {self.first_name[0]}."
    
    
    def name_dict(self):
        return {
            "last_name": self.last_name,
            "first_name": self.first_name,
            "display_name": self.display_name,
        }
    
    def __le__(self, other):
        if self.is_superuser:
            return other.is_superuser
        # all superusers are staff by default. We assume that here.
        if self.is_staff:
            return other.is_staff
        if self.teacher:
            return other.teacher or other.is_staff
        return True
    
    def __ge__(self, other):
        return other <= self
    
    def __str__(self):
        return self.get_full_name()

class AnonymousUser(AnonymousUser):
    teacher = False
    title = ""
    roles = umr.Roles()

class ColleGroup(models.Model):

    class Meta:
        verbose_name = "Groupes de colle"

    nb = models.SmallIntegerField(verbose_name="Numéro")
    void = models.BooleanField(verbose_name="Groupe vide", default=False)
    level = models.ForeignKey(umr.Level, on_delete=models.CASCADE,
        verbose_name="Classe", default=umr.get_default_level)

    def __str__(self):
        return f"Groupe n°{self.nb}"
    
    def students(self):
        return [stg.user.pk for stg in self.studentcollegroup_set.all()]


class SCGManager(models.Manager):
    """
    Automatic select_related
    """

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.select_related("group", "user")


class StudentColleGroup(models.Model):
    """
    Colle group for students
    """

    class Meta:
        unique_together = ["user", "group"]
        verbose_name = "Groupe de l'étudiant"
        verbose_name_plural = "Groupes des étudiants"
        ordering = ["user__last_name", "user__first_name"]

    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Utilisateur",
        related_name="studentcollegroup")
    group = models.ForeignKey(ColleGroup, on_delete=models.CASCADE, verbose_name="Groupe de colle")

    objects = SCGManager()

    @property
    def colle_group(self):
        return self.group.nb

    def __str__(self):
        return "%s, groupe %i" % (str(self.user), self.colle_group)

class UserPref(models.Model):

    class Meta:
        verbose_name = "Préférence utilisateur"
    
    user = models.OneToOneField(User, models.CASCADE, verbose_name="Utilisateur")
    dark_theme = models.BooleanField(default=False, verbose_name="Mode sombre par défaut")

    def to_context_data(self):
        ctx = {"dark_theme": self.dark_theme}
        return ctx
    
    def __str__(self):
        return str(self.user)