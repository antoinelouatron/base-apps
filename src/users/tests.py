"""
date: 2024-03-30
"""

from django.contrib.sessions.backends.db import SessionStore
from django.test import RequestFactory

from dev.test_utils import TestCase
from dev.test_data import CreateUserMixin
from dev.test_view import JsonURL, TestURL
import users.emailbackend as ueb
import users.forms as uf
import users.forms.imports as ufi
import users.middlewares as umw
import users.models as um
import users.permissions as up
User = um.User

class TestModels(TestCase):

    def test_user_creation(self):
        u1 = um.User.objects.create(email="moia@example.com")
        self.assertIsNotNone(u1.id)
        self.assertFalse(u1.teacher)
        u2 = um.User.objects.create(email="moi2@example.com")
        self.assertFalse(u2.teacher)
        level = um.Level.objects.create(name="L1")
        subject = um.Subject.objects.create(name="S1", level=level)
        u3 = um.User.objects.create_teacher(email="moi3@example.com",
            subject=subject)
        self.assertTrue(u3.teacher)
        u4 = um.User.objects.create_student(username="student")
        self.assertFalse(u4.teacher)
        self.assertEqual(um.ColleGroup.objects.count(), 0)
        self.assertEqual(u4.studentcollegroup.count(), 0)
        u5 = um.User.objects.create_student(username="student2", colle_group=1)
        self.assertFalse(u5.teacher)
        self.assertEqual(um.ColleGroup.objects.count(), 1)
        self.assertEqual(u5.studentcollegroup.count(), 1)
        # same ColleGroup is used
        u6 = um.User.objects.create_student(username="student3", colle_group=1)
        self.assertFalse(u6.teacher)
        self.assertEqual(um.ColleGroup.objects.count(), 1)
        self.assertEqual(u6.studentcollegroup.first().colle_group, 1)
    
    def test_user_full_name(self):
        u1 = um.User.objects.create(last_name="moi", first_name="aa")
        self.assertEqual(u1.get_full_name(), "moi aa")
        u2 = um.User.objects.create(last_name="moi", first_name="aa", title="M.")
        self.assertEqual(u2.get_full_name(), "M. moi")
        self.assertEqual(u2.get_full_name(), u2.display_name)
        self.assertEqual(u2.short_name, "moi a.")
    
    # def test_username_creation(self):
    #     first = "nam"
    #     last = "ema"
    #     for i in range(3):
    #         user = um.User.objects.create(
    #             first_name=first,
    #             last_name=last,)
    #         self.assertEqual(len(user.username), 4)
    #     user = um.User.objects.create(
    #             first_name=first,
    #             last_name=last,)
    #     self.assertEqual(len(user.username), 8)
    
    def test_signal(self):
        level = um.Level.objects.create(name="L1")
        st1 = um.User.objects.create_student(username="student", level=level)
        self.assertFalse(st1.teacher)
        self.assertTrue(st1.student)
        st1.is_active = False
        st1.save()
        st1.refresh_from_db()
        self.assertFalse(st1.teacher)
        self.assertFalse(st1.student)
    
    # User comparison
    def test_le_superuser(self):
        user1 = User(is_superuser=True, is_staff=True)
        user2 = User(is_staff=True, is_superuser=False)
        self.assertTrue(user1.is_superuser)
        self.assertTrue(user1 >= user2)
        self.assertTrue(user2 <= user1)
        self.assertFalse(user1 <= user2)
        self.assertFalse(user2 >= user1)

    def test_le_staff(self):
        user1 = User(is_superuser=False, is_staff=True)
        user2 = User(is_superuser=False, is_staff=False)
        self.assertTrue(user1 >= user2)
        self.assertTrue(user2 <= user1)
        self.assertFalse(user1 <= user2)
        self.assertFalse(user2 >= user1)

    def test_le_teacher(self):
        user1 = User(is_superuser=False, is_staff=False)
        user2 = User(is_superuser=False, is_staff=False)
        level = um.Level.objects.create(name="L1")
        subject = um.Subject.objects.create(name="S1", level=level)
        user1.roles.add(um.AtomicRole.create(teacher=True, subject=subject))
        self.assertTrue(user1 >= user2)
        self.assertTrue(user2 <= user1)
        self.assertFalse(user1 <= user2)
        self.assertFalse(user2 >= user1)

    def test_le_default(self):
        user1 = User(is_superuser=False, is_staff=False)
        user2 = User(is_superuser=False, is_staff=False)
        self.assertTrue(user1 >= user2)
        self.assertTrue(user2 <= user1)
        self.assertTrue(user1 <= user2)
        self.assertTrue(user2 >= user1)

class TestUserPref(TestCase, CreateUserMixin):

    def test_context(self):
        self.create_users()
        pref = self.staff_user.prefs
        ctx = pref.to_context_data()
        self.assertIn("dark_theme", ctx)
        self.assertFalse(ctx["dark_theme"])
        pref.dark_theme = True
        ctx = pref.to_context_data()
        self.assertIn("dark_theme", ctx)
        self.assertTrue(ctx["dark_theme"])
        self.assertEqual(str(pref), str(pref.user))
    
    def test_ajax_view(self):
        url = JsonURL(self, "users", "edit_prefs", status=403) #login !
        url.test(forbidden=True)
        self.create_users()
        url.set_user(self.staff_user)
        # no get
        url.test(forbidden=True)
        url.method = "post"
        url.status = 200
        url.test()
        url.data = {
            "dark_theme": True
        }
        url.test()
        self.staff_user.refresh_from_db()
        self.assertTrue(self.staff_user.userpref.dark_theme)
    
    def test_cookie_precedence(self):
        self.create_users()
        pref = self.staff_user.prefs
        url = TestURL(self, "", "account_login", status=200)
        resp = url.test()
        self.assertNotIn("dark_theme", resp.context)
        url.user = self.staff_user
        resp = url.test()
        self.assertIn("dark_theme", resp.context)
        self.assertFalse(resp.context["dark_theme"])
        pref.dark_theme = True
        pref.save()
        resp = url.test()
        self.assertIn("dark_theme", resp.context)
        self.assertTrue(resp.context["dark_theme"])
        resp = url.test(cookies={"darktheme": "disabled"})
        self.assertIn("dark_theme", resp.context)
        self.assertFalse(resp.context["dark_theme"])
    
class TestUserAtomicForm(TestCase, CreateUserMixin):

    def test_no_commit(self):
        data = {
            "first_name": "Test",
            "last_name": "User",
            "email": "test@example.com",
            "colle_group": 1
        }
        level = um.get_default_level(instance=True)
        role = um.AtomicRole.create(student=True, level=level)
        form = ufi.UserAtomicForm(data=data, role=role)
        # needed by post_save
        form.master_form = ufi.BaseImportForm()
        self.assertTrue(form.is_valid(), "No commit, no user")
        user = form.save(commit=False)
        user = form.post_save(commit=False) # called by FileImportForm
        self.assertIsNone(user.id, "No user created")
        self.assertEqual(um.StudentColleGroup.objects.count(), 0, "No group created")
        user.save()
        self.assertIsNotNone(user.id, "User created")
        form.save_m2m()
        self.assertEqual(um.StudentColleGroup.objects.count(), 1, "Group created")

class TestPermissions(TestCase, CreateUserMixin):

    def test_student(self):
        self.create_users()
        user = self.users[0]
        level1 = um.Level.objects.create(name="Level 1")
        level2 = um.Level.objects.create(name="Level 2")
        self.assertFalse(up.STUDENT.has_permission(user, level1))
        self.assertFalse(up.STUDENT.has_permission(user, level2))
        user.roles.add(um.AtomicRole.create(student=True, level=level1))
        user.save()
        self.assertTrue(user.roles.is_student(level1))
        self.assertTrue(up.STUDENT.has_permission(user, level1))
        self.assertFalse(up.STUDENT.has_permission(user, level2))

        # check other permissions
        self.assertFalse(up.TEACHER.has_permission(user, level1))
        self.assertFalse(up.TEACHER.has_permission(user, level2))
        self.assertFalse(up.COLLEUR.has_permission(user, level1))
        self.assertFalse(up.COLLEUR.has_permission(user, level2))
        self.assertFalse(up.SECRETARY.has_permission(user, level1))
        self.assertFalse(up.SECRETARY.has_permission(user, level2)) 
        self.assertFalse(up.SCHOOL_ADMIN.has_permission(user, level1))
        self.assertFalse(up.SCHOOL_ADMIN.has_permission(user, level2))

        # check operators
        self.assertTrue((~up.TEACHER).has_permission(user, level1))
        self.assertTrue((up.TEACHER | up.STUDENT).has_permission(user, level1))
        self.assertFalse((up.TEACHER & up.STUDENT).has_permission(user, level1))
    
    def test_allow_all(self):
        self.create_users()
        user = self.users[0]
        level1 = um.Level.objects.create(name="Level 1")
        subject = um.Subject.objects.create(name="Subject 1", level=level1)
         # no role
        self.assertTrue(up.AllowAll().has_permission(user))
        self.assertTrue(up.AllowAll().has_permission(user, level1))
        self.assertTrue(up.AllowAll().has_permission(user, subject=subject))
    
    def test_strict_teacher(self):
        self.create_users()
        user = self.users[0]
        level1 = um.Level.objects.create(name="Level 1")
        subject = um.Subject.objects.create(name="subject", level=level1)
        subject2 = um.Subject.objects.create(name="subject2", level=level1)
        user.roles.add(um.AtomicRole.create(teacher=True,subject=subject))
        user.save()
        perm = up.IsTeacher(strict=True)
        self.assertTrue(perm.has_permission(user, subject=subject))
        self.assertFalse(perm.has_permission(user, subject=subject2))
        self.assertFalse(perm.has_permission(user, level=level1))
        perm.strict = False
        self.assertTrue(perm.has_permission(user, level=level1))


class TestEMailBackend(TestCase):

    def setUp(self):
        self.backend = ueb.EMailBackend()
        self.user = um.User.objects.create_user("mail", "mail@example.com")
        self.user.set_password("secret")
        self.user.save()

    def test_valid_credentials(self):
        user = self.backend.authenticate(
            None, username="Mail@Example.com", password="secret")
        self.assertEqual(user, self.user)

    def test_wrong_password(self):
        self.assertIsNone(self.backend.authenticate(
            None, username="mail@example.com", password="wrong"))

    def test_unknown_email(self):
        self.assertIsNone(self.backend.authenticate(
            None, username="ghost@example.com", password="secret"))

    def test_inactive_user_rejected(self):
        # un utilisateur désactivé ne doit pas pouvoir s'authentifier
        self.user.is_active = False
        self.user.save()
        self.assertIsNone(self.backend.authenticate(
            None, username="mail@example.com", password="secret"))


class TestSeeAsMiddleware(TestCase):

    def setUp(self):
        self.factory = RequestFactory()
        # get_response identité : on inspecte la requête après middleware
        self.mw = umw.SeeAsMiddleware(lambda request: request)
        self.level = um.Level.objects.create(name="L1")
        subject = um.Subject.objects.create(name="Maths", level=self.level)
        self.teacher = um.User.objects.create_user("teach", "teach@example.com")
        self.teacher.roles.add(um.AtomicRole.create(teacher=True, subject=subject))
        self.teacher.save()
        self.student = um.User.objects.create_student(
            username="stud", email="stud@example.com", level=self.level)
        self.admin = um.User.objects.create_superuser(
            "root", "root@example.com", "pw")

    def _request(self, user, **params):
        request = self.factory.get("/", params)
        request.user = user
        request.session = SessionStore()
        return self.mw(request)

    def test_teacher_sees_as_student(self):
        request = self._request(self.teacher, see_as=self.student.pk)
        self.assertEqual(request.user, self.student)
        self.assertEqual(request.session.get("see_as"), str(self.student.pk))

    def test_teacher_cannot_see_as_superuser(self):
        # cible refusée : requête anonymisée, session non polluée
        request = self._request(self.teacher, see_as=self.admin.pk)
        self.assertFalse(request.user.is_authenticated)
        self.assertNotIn("see_as", request.session)

    def test_invalid_target_not_stored(self):
        # id inexistant : la session ne doit pas conserver la valeur
        request = self._request(self.teacher, see_as=99999)
        self.assertFalse(request.user.is_authenticated)
        self.assertNotIn("see_as", request.session)

    def test_non_numeric_target(self):
        # valeur non numérique : pas d'erreur 500
        request = self._request(self.teacher, see_as="abc")
        self.assertFalse(request.user.is_authenticated)
        self.assertNotIn("see_as", request.session)

    def test_student_cannot_use_see_as(self):
        request = self._request(self.student, see_as=self.teacher.pk)
        self.assertEqual(request.user, self.student)
        self.assertNotIn("see_as", request.session)

    def test_reset_user(self):
        request = self.factory.get("/", {"reset_user": "1"})
        request.user = self.teacher
        request.session = SessionStore()
        request.session["see_as"] = str(self.student.pk)
        request = self.mw(request)
        self.assertNotIn("see_as", request.session)