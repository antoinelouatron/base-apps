"""
date: 2025-07-23
"""

import abc

class Permission(abc.ABC):
    """
    Abstract base class for permissions.

    Supports logical operations like AND (&), OR (|), and NOT (~).
    """
    
    @abc.abstractmethod
    def has_permission(self, user, level=None, subject=None) -> bool:
        """
        Check if the user has permission to perform an action on the object.
        """
        pass

    def __or__(self, other: "Permission") -> "Permission":
        return _OR(self, other)
    
    def __and__(self, other: "Permission") -> "Permission":
        return _AND(self, other)

    def __invert__(self) -> "Permission":
        return _NOT(self)

class AllowAll(Permission):
    """
    Permission that allows all actions.
    """
    
    def has_permission(self, user, level=None, subject=None) -> bool:
        return True

class _OR(Permission):
    """
    OR permission, checks if any of the given permissions are granted.
    """
    
    def __init__(self, *permissions: Permission):
        self.permissions = permissions
    
    def has_permission(self, user, level=None, subject=None) -> bool:
        return any(p.has_permission(user, level, subject) for p in self.permissions)

class _AND(Permission):
    """
    AND permission, checks if all of the given permissions are granted.
    """
    
    def __init__(self, *permissions: Permission):
        self.permissions = permissions
    
    def has_permission(self, user, level=None, subject=None) -> bool:
        return all(p.has_permission(user, level, subject) for p in self.permissions)

class _NOT(Permission):
    """
    NOT permission, checks if the given permission is not granted.
    """
    
    def __init__(self, permission: Permission):
        self.permission = permission
    
    def has_permission(self, user, level=None, subject=None) -> bool:
        return not self.permission.has_permission(user, level, subject)

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
    
    def has_permission(self, user, level=None, subject=None) -> bool:
        return user.is_authenticated and user.roles.is_teacher(level=level, subject=subject)

class IsColleur(Permission):
    """
    Permission for colleur role.
    """
    
    def has_permission(self, user, level=None, subject=None) -> bool:
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

STUDENT = IsStudent()
TEACHER = IsTeacher()
COLLEUR = IsColleur()
SECRETARY = IsSecretary()
SCHOOL_ADMIN = IsAdmin()
REF_TEACHER = IsRefTeacher()