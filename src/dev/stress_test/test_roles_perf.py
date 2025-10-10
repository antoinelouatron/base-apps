from time import perf_counter

from django.test import tag

from dev.test_utils import TestCase
from dev.test_data import CreateUserMixin

import users.models as um

class RolesFilterTest(TestCase, CreateUserMixin):
    """
    Test the Roles filter.
    """
    USER_COUNT = 10000

    def populate(self):
        self.create_users(self.USER_COUNT)
        self.level = um.Level.objects.create(name="Test Level", first_year=True,
            student_count=15)
        self.subject = um.Subject.objects.create(name="Test Subject",
            level=self.level)

    @tag("download") # excluded by default
    def test_roles_set(self):
        self.populate()
        users = list(um.User.objects.all())
        start = perf_counter()
        for user in users:
            user.roles.set([
                um.AtomicRole.create(student=True, level=self.level.pk),
                um.AtomicRole.create(teacher=True, level=self.level.pk, subject=self.subject.pk)
            ])
        um.User.objects.bulk_update(
            users, ["roles"]
        )
        end = perf_counter()
        print(f"Set roles for {self.USER_COUNT} users in {end-start:.2f} seconds")
        self.assertEqual(um.User.objects.count(), self.USER_COUNT+2)
        # self.assertEqual(um.User.objects.students(self.level).count(), self.USER_COUNT)
        # self.assertEqual(um.User.objects.teachers(self.subject).count(), self.USER_COUNT)
    
    @tag("download") # excluded by default
    def test_roles_filter(self):
        self.populate()
        users = list(um.User.objects.all())
        for user in users:
            user.roles.set([
                um.AtomicRole.create(student=True, level=self.level.pk),
                um.AtomicRole.create(teacher=True, level=self.level.pk, subject=self.subject.pk)
            ])
        um.User.objects.bulk_update(
            users, ["roles"]
        )
        self.assertEqual(um.User.objects.count(), self.USER_COUNT+2)
        start = perf_counter()
        for k in range(50):
            students = um.User.objects.students(self.level)
            teachers = um.User.objects.teachers(self.subject)
            self.assertEqual(students.count(), self.USER_COUNT+2)
            self.assertEqual(teachers.count(), self.USER_COUNT+2)
        end = perf_counter()
        print(f"Filtered roles for {self.USER_COUNT} users in {end-start:.2f} seconds")
