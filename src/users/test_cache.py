from dev.test_utils import TestCase
import users.models as um
from users.cache import subjects, teachers, colleurs

class CacheTestCase(TestCase):
    def test_subject_cache(self):
        self.assertTrue(subjects.stale)
        self.assertIsNone(subjects.get("invalid"))
        self.assertFalse(subjects.stale)
        level = um.Level.objects.create(name="L1")
        subject = um.Subject.objects.create(name="Maths", level=level)
        self.assertTrue(subjects.stale)
        self.assertEqual(subjects.get(str(subject.pk)), level)
        self.assertEqual(subjects[subject], level)

    def test_user_cache(self):
        level = um.Level.objects.create(name="L1")
        subject = um.Subject.objects.create(name="Maths", level=level)
        teacher = um.User.objects.create_teacher(
            first_name="John",
            last_name="Doe",
            email="john.doe@example.com",
            subject=subject
        )
        colleur = um.User.objects.create_colleur(
            first_name="Jane",
            last_name="Smith",
            email="jane.smith@example.com",
            subject=subject
        )
        self.assertTrue(teachers.stale)
        self.assertTrue(colleurs.stale)
        self.assertIn(teacher, teachers[level])
        self.assertIn(colleur, colleurs[level])
        self.assertFalse(teachers.stale)
        self.assertFalse(colleurs.stale)