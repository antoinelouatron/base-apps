"""
date: 2025-07-22
"""
from dev.test_data import CreateUserMixin
from dev.test_utils import TestCase
import users.models as um

class TestRoles(CreateUserMixin, TestCase):

    def setUp(self):
        super().setUp()
        self.create_users(3)
        self.level = um.Level.objects.create(name="Test Level", first_year=True,
            student_count=15)
        self.subject = um.Subject.objects.create(name="Test Subject",
            level=self.level)

    def test_level_ors(self):
        level = self.level
        self.assertEqual(level.ORS(), 11)

        level.student_count = 25
        self.assertEqual(level.ORS(), 10)

        level.student_count = 40
        self.assertEqual(level.ORS(), 9)

        level.first_year = False
        level.student_count = 15
        self.assertEqual(level.ORS(), 10)
        level.student_count = 25
        self.assertEqual(level.ORS(), 9)
        level.student_count = 40
        self.assertEqual(level.ORS(), 8)
    
    def test_atomic_role_creation(self):
        role = um.AtomicRole.create(student=True, level=self.level)
        # all level/subject are converted to strings if not None
        self.assertEqual(role.level, str(self.level.pk))
        self.assertIsNone(role.subject)
        self.assertEqual(role.role, um.AtomicRole.STUDENT)

        role = um.AtomicRole.create(teacher=True, level=self.level, subject=self.subject)
        self.assertEqual(role.level, str(self.level.pk))
        self.assertEqual(role.subject, str(self.subject.pk))
        self.assertEqual(role.role, um.AtomicRole.TEACHER)

        role = um.AtomicRole.create(colleur=True, level=self.level, subject=self.subject)
        self.assertEqual(role.level, str(self.level.pk))
        self.assertEqual(role.subject, str(self.subject.pk))
        self.assertEqual(role.role, um.AtomicRole.COLLEUR)

        role = um.AtomicRole.create(secretary=True)
        self.assertIsNone(role.level)
        self.assertIsNone(role.subject)
        self.assertEqual(role.role, um.AtomicRole.SECRETARY)

        role = um.AtomicRole.create(school_admin=True)
        self.assertIsNone(role.level)
        self.assertIsNone(role.subject)
        self.assertEqual(role.role, um.AtomicRole.SCHOOL_ADMIN)

        role = um.AtomicRole.create()
        self.assertEqual(role.role, um.AtomicRole.NONE)
    
    def test_role_creation_errors(self):
        with self.assertRaises(ValueError):
            um.AtomicRole.create(teacher=True, level=self.level)

        with self.assertRaises(ValueError):
            um.AtomicRole.create(colleur=True, level=self.level)

        with self.assertRaises(ValueError):
            um.AtomicRole.create(student=True)

        with self.assertRaises(ValueError):
            um.AtomicRole(role="invalid_role_do_not_use_this!")
    
    def test_role_fields(self):
        user = um.User.objects.first() # from db
        self.assertIsInstance(user.roles, um.Roles)
        self.assertFalse(user.roles.is_student(level=self.level))
        self.assertFalse(user.roles.is_student())
        user.roles.add(um.AtomicRole.create(student=True, level=self.level.pk))
        self.assertTrue(user.roles.is_student(level=self.level))
        self.assertFalse(user.roles.is_teacher(subject=self.subject))
        self.assertFalse(user.roles.is_colleur(subject=self.subject))
        self.assertFalse(user.roles.is_secretary())
        self.assertFalse(user.roles.is_admin())

        user.roles.add(um.AtomicRole.create(teacher=True, level=self.level.pk, subject=self.subject.pk))
        self.assertTrue(user.roles.is_student(level=self.level))
        self.assertTrue(user.roles.is_teacher(subject=self.subject))
        self.assertFalse(user.roles.is_colleur(subject=self.subject))
        self.assertFalse(user.roles.is_secretary())
        self.assertFalse(user.roles.is_admin())
        self.assertEqual(len(user.roles.display_data(
            {str(self.level.pk): self.level}, {str(self.subject.pk): self.subject})), 2)

        user.roles.set([])
        self.assertFalse(user.roles.is_student(level=self.level))
        self.assertFalse(user.roles.is_teacher(subject=self.subject))
    
    def test_role_deletion(self):
        user = um.User.objects.first()
        user.roles.add(um.AtomicRole.create(student=True, level=self.level.pk))
        user.save()
        self.assertTrue(user.roles.is_student(level=self.level))
        user.roles.set([])
        self.assertFalse(user.roles.is_student(level=self.level))
        user.roles.add(um.AtomicRole.create(teacher=True, subject=self.subject.pk))
        user.save()
        self.assertTrue(user.roles.is_teacher(subject=self.subject))
        user.roles.remove(um.AtomicRole.create(teacher=True, subject=self.subject.pk))
        user.save()
        self.assertFalse(user.roles.is_teacher(subject=self.subject))
        user.roles.add(um.AtomicRole.create(school_admin=True))
        user.save()
        self.assertTrue(user.roles.is_admin())
        user.roles.remove(um.AtomicRole.create(school_admin=True))
        user.save()
        self.assertFalse(user.roles.is_admin())
        user.roles.add(um.AtomicRole.create(student=True, level=self.level.pk))
        user.save()
        self.assertTrue(user.roles.is_student(level=self.level))
        user.roles.remove(um.AtomicRole.create(student=True, level=self.level.pk))
        user.save()
        self.assertFalse(user.roles.is_student(level=self.level))
        user.roles.add(um.AtomicRole.create(ref_teacher=True, level=self.level.pk))
        user.save()
        self.assertTrue(user.roles.is_ref_teacher(level=self.level))
        user.roles.remove(um.AtomicRole.create(ref_teacher=True, level=self.level.pk))
        user.save()
        self.assertFalse(user.roles.is_ref_teacher(level=self.level))

    def test_equality(self):
        role1 = um.AtomicRole.create(student=True, level=self.level.pk)
        role2 = um.AtomicRole.create(student=True, level=self.level.pk)
        role3 = um.AtomicRole.create(teacher=True, subject=self.subject.pk)

        self.assertEqual(role1, role2)
        self.assertNotEqual(role1, role3)
        self.assertNotEqual(role1, {"role": "s", "level": str(self.level.pk), "subject": None})
    
    # def test_repr(self):
    #     role = um.AtomicRole.create(student=True, level=self.level.pk)
    #     s = repr(role)
    #     new_obj = eval(s, locals={"AtomicRole": um.AtomicRole})
    #     self.assertEqual(role, new_obj)

    def test_roles_iteration(self):
        user = um.User.objects.first()
        user.roles.add(um.AtomicRole.create(student=True, level=self.level.pk))
        user.roles.add(um.AtomicRole.create(teacher=True, subject=self.subject.pk))
        user.roles.add(um.AtomicRole.create(school_admin=True))
        user.save()

        roles = list(user.roles)
        self.assertEqual(len(roles), 3)
        self.assertIn(um.AtomicRole.create(student=True, level=self.level.pk), roles)
        self.assertIn(um.AtomicRole.create(teacher=True, subject=self.subject.pk), roles)
        self.assertIn(um.AtomicRole.create(school_admin=True), roles)

        user.roles.set([])
        roles = list(user.roles)
        self.assertEqual(len(roles), 0)

        # New : multiple level for ref_teacher
        user.roles.add(um.AtomicRole.create(ref_teacher=True, level=self.level.pk))
        user.roles.add(um.AtomicRole.create(ref_teacher=True, level=self.level.pk + 1))
        user.save() 
        roles = list(user.roles)
        self.assertEqual(len(roles), 2)
        self.assertIn(um.AtomicRole.create(ref_teacher=True, level=self.level.pk), roles)
        self.assertIn(um.AtomicRole.create(ref_teacher=True, level=self.level.pk + 1), roles)
    
    def test_getitem(self):
        roles = um.Roles()
        self.assertFalse(roles[um.AtomicRole.SECRETARY])
        roles.add(um.AtomicRole.create(secretary=True))
        self.assertTrue(roles[um.AtomicRole.SECRETARY])

        with self.assertRaises(KeyError):
            roles["invalid_role"]
    
    def test_level_manager(self):
        self.assertEqual(um.User.objects.level(self.level).count(), 0)
        user1, user2, user3 = self.users
        user1.roles.add(um.AtomicRole.create(student=True, level=self.level.pk))
        user1.save()
        self.assertEqual(um.User.objects.level(self.level).count(), 1)
        subject = um.Subject.objects.create(name="Another Subject", level=self.level)
        user2.roles.add(um.AtomicRole.create(teacher=True, subject=subject.pk))
        user2.save()
        self.assertEqual(um.User.objects.teachers(subject).count(), 1)
        self.assertEqual(um.User.objects.level(self.level).count(), 2)
        user3.roles.add(um.AtomicRole.create(colleur=True, subject=self.subject.pk))
        user3.save()
        self.assertEqual(um.User.objects.colleurs(self.subject).count(), 1)
        self.assertEqual(um.User.objects.level(self.level).count(), 3)
    
    def test_display_data(self):
        user = um.User.objects.first()
        subject2 = um.Subject.objects.create(name="Info", level=self.level)
        user.roles.add(um.AtomicRole.create(teacher=True, subject=self.subject.pk))
        user.roles.add(um.AtomicRole.create(teacher=True, subject=subject2.pk))
        #user.roles.add(um.AtomicRole.create(school_admin=True))
        user.save()

        display_data = user.roles.display_data(
            {str(self.level.pk): self.level},
            {str(self.subject.pk): self.subject, str(subject2.pk): subject2}
        )
        self.assertEqual(len(display_data), 2)
        rol1 = display_data[0]
        rol2 = display_data[1]
        #rol3 = display_data[2]
        self.assertFalse(rol1["protected"])
        self.assertFalse(rol2["protected"])
        #self.assertTrue(rol3["protected"])
        # check preposition "de" or "d'"
        self.assertIn("de", rol1["role"])
        self.assertIn("d'", rol2["role"])

        # check protected roles
        user.roles.set([um.AtomicRole.create(school_admin=True),
                        um.AtomicRole.create(secretary=True)])
        user.save()
        display_data = user.roles.display_data({}, {})
        self.assertEqual(len(display_data), 2)
        rol1 = display_data[0]
        rol2 = display_data[1]
        self.assertTrue(rol1["protected"])
        self.assertTrue(rol2["protected"])
    
    def test_cached_properties(self):
        user = um.User.objects.first()
        self.assertEqual(user.roles.teacher_subjects, [])
        user.roles.add(um.AtomicRole.create(teacher=True, subject=self.subject))
        user.save()
        self.assertEqual(len(user.roles.teacher_subjects), 0) # cached
        user.refresh_from_db()
        self.assertEqual(len(user.roles.teacher_subjects), 1)
        self.assertEqual(len(user.roles.teacher_levels), 1)
        self.assertIn(self.level, user.roles.teacher_levels)

        self.assertEqual(len(user.roles.colleur_subjects), 0)
        self.assertEqual(len(user.roles.student_levels), 0)
        user.roles.set([
            um.AtomicRole.create(colleur=True, subject=self.subject),
            um.AtomicRole.create(student=True, level=self.level)
        ])
        user.save()
        self.assertEqual(len(user.roles.colleur_subjects), 0)
        self.assertEqual(len(user.roles.student_levels), 0)
        user.refresh_from_db()
        self.assertEqual(len(user.roles.colleur_subjects), 1)
        self.assertEqual(len(user.roles.student_levels), 1)

class TestUserManager(CreateUserMixin, TestCase):

    def setUp(self):
        super().setUp()
        self.create_users(3)
        self.level = um.Level.objects.create(name="Test Level", first_year=True,
            student_count=15)
        self.subject = um.Subject.objects.create(name="Test Subject",
            level=self.level)
    
    def test_students(self):
        user = um.User.objects.first()
        user.roles.add(um.AtomicRole.create(student=True, level=self.level.pk))
        user.save()
        self.assertTrue(user.roles.is_student(level=self.level))
        students = um.User.objects.students(self.level)
        self.assertIn(user, students)
        self.assertEqual(students.count(), 1)

    def test_multiple(self):
        user1 = um.User.objects.first()
        user1.roles.add(um.AtomicRole.create(student=True, level=self.level.pk))
        user1.save()

        user2 = um.User.objects.create(
            first_name="Test",
            last_name="User",
            email="test@example.com",
            username="testuser"
        )
        user2.roles.add(um.AtomicRole.create(student=True, level=self.level.pk))
        user2.save()

        students = um.User.objects.students(self.level)
        self.assertIn(user1, students)
        self.assertIn(user2, students)
        self.assertEqual(students.count(), 2)

        user1.roles.add(um.AtomicRole.create(teacher=True, level=self.level.pk, subject=self.subject.pk))
        user1.save()
        self.assertTrue(user1.roles.is_teacher(subject=self.subject))
        self.assertEqual(um.User.objects.teachers(self.subject).count(), 1)

        self.assertIn(user1, um.User.objects.teachers(self.subject))
        self.assertNotIn(user2, um.User.objects.teachers(self.subject))

        user2.roles.add(um.AtomicRole.create(colleur=True, level=self.level.pk,
            subject=self.subject.pk))
        user2.save()
        self.assertTrue(user2.roles.is_colleur(subject=self.subject))
        self.assertEqual(um.User.objects.colleurs(self.subject).count(), 1)

        self.assertEqual(um.User.objects.secretaries().count(), 0)
        self.assertEqual(um.User.objects.school_admins().count(), 0)

        user3 = um.User.objects.create(
            first_name="Admin",
            last_name="User",
            email="admin@example.com")
        user3.roles.add(um.AtomicRole.create(school_admin=True))
        user3.save()
        self.assertTrue(user3.roles.is_admin())
        self.assertEqual(um.User.objects.school_admins().count(), 1)

        user4 = um.User.objects.create(
            first_name="Secretary",
            last_name="User",
            email="secretary@example.com")
        user4.roles.add(um.AtomicRole.create(secretary=True))
        user4.save()
        self.assertTrue(user4.roles.is_secretary())
        self.assertEqual(um.User.objects.secretaries().count(), 1)
        self.assertEqual(um.User.objects.teachers(self.subject).count(), 1)
        self.assertEqual(um.User.objects.colleurs(self.subject).count(), 1)
        self.assertEqual(um.User.objects.students(self.level).count(), 2)