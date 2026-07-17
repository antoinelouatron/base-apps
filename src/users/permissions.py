"""
date: 2025-07-23

Permissions concrètes liées aux rôles du modèle User. La structure
combinatoire générique (Permission, AllowAll, & | ~) vit dans utils.permissions.
On la ré-exporte ici pour compatibilité des imports existants (up.AllowAll, ...).
"""

import users.cache as uc
from utils.permissions import Permission, AllowAll, _OR, _AND, _NOT  # noqa: F401


class IsStudent(Permission):
    """
    Permission for student role.
    """

    def has_permission(self, user, level=None, subject=None) -> bool:
        return user.is_authenticated and user.roles.is_student(level)

class IsTeacher(Permission):
    """
    Permission for teacher role.
    """

    def __init__(self, strict=False):
        self.strict = strict

    def has_permission(self, user, level=None, subject=None) -> bool:
        if self.strict:
            return subject is not None and user.is_authenticated and user.roles.is_teacher(subject=subject)
        if level is not None:
            return user in uc.teachers.get(level)
        return user.is_authenticated and user.roles.is_teacher(level=level, subject=subject)

class IsColleur(Permission):
    """
    Permission for colleur role.
    """

    def has_permission(self, user, level=None, subject=None) -> bool:
        if level is not None:
            return user in uc.colleurs.get(level)
        return user.is_authenticated and user.roles.is_colleur(level=level, subject=subject)

class IsSecretary(Permission):
    """
    Permission for secretary role.
    """

    def has_permission(self, user, level=None, subject=None) -> bool:
        return user.is_authenticated and user.roles.is_secretary()

class IsAdmin(Permission):
    """
    Permission for school admin role.
    """

    def has_permission(self, user, level=None, subject=None) -> bool:
        return user.is_authenticated and user.roles.is_admin()

class IsRefTeacher(Permission):
    """
    Permission for referent teacher role.
    """

    def has_permission(self, user, level=None, subject=None) -> bool:
        return user.is_authenticated and user.roles.is_ref_teacher(level)

class IsSuperUser(Permission):
    """
    Permission for superusers.
    """

    def has_permission(self, user, level=None, subject=None) -> bool:
        return user.is_authenticated and user.is_superuser

STUDENT = IsStudent()
TEACHER = IsTeacher()
COLLEUR = IsColleur()
SECRETARY = IsSecretary()
SCHOOL_ADMIN = IsAdmin()
REF_TEACHER = IsRefTeacher()
SUPERUSER = IsSuperUser()

# Permission concrète consommée par base_archives via le hook settings
# ARCHIVES_DOWNLOAD_PERMISSION (cf. base_archives.views).
ARCHIVES_DOWNLOAD = SECRETARY | SCHOOL_ADMIN
