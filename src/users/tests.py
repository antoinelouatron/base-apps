"""
date: 2024-03-30
"""

from dev.test_utils import TestCase
from dev.test_data import CreateUserMixin
from dev.test_view import JsonURL, TestURL
import users.forms as uf
import users.models as um
import users.permissions as up
User = um.User

class TestModels(TestCase):

    def test_user_creation(self):
        # minimal data
        with self.assertRaises(ValueError):
            um.User.objects.create(last_name="moia")
        with self.assertRaises(ValueError):
            um.User.objects.create(first_name="moia")
        u1 = um.User.objects.create(username="moia")
        self.assertIsNotNone(u1.id)
        self.assertFalse(u1.teacher)
        u2 = um.User.objects.create(last_name="moi", first_name="aa")
        self.assertEqual(u2.username, "moaa")
        self.assertFalse(u2.teacher)
        u3 = um.User.objects.create_teacher(last_name="moi", first_name="aa")
        self.assertTrue(u3.teacher)
        self.assertEqual(u3.username, "maa")
        u3 = um.User.objects.create_teacher(last_name="moi", first_name="aa")
        self.assertTrue(u3.teacher)
        self.assertNotEqual(u3.username, "maa")
        self.assertEqual(len(u3.username), 8, "default random length")
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
    
    def test_username_creation(self):
        first = "nam"
        last = "ema"
        for i in range(3):
            user = um.User.objects.create(
                first_name=first,
                last_name=last,)
            self.assertEqual(len(user.username), 4)
        user = um.User.objects.create(
                first_name=first,
                last_name=last,)
        self.assertEqual(len(user.username), 8)
    
    def test_signal(self):
        st1 = um.User.objects.create_student(username="student")
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
        user1 = User(is_superuser=False, is_staff=False, teacher=True)
        user2 = User(is_superuser=False, is_staff=False, teacher=False)
        self.assertTrue(user1 >= user2)
        self.assertTrue(user2 <= user1)
        self.assertFalse(user1 <= user2)
        self.assertFalse(user2 >= user1)

    def test_le_default(self):
        user1 = User(is_superuser=False, is_staff=False, teacher=False)
        user2 = User(is_superuser=False, is_staff=False, teacher=False)
        self.assertTrue(user1 >= user2)
        self.assertTrue(user2 <= user1)
        self.assertTrue(user1 <= user2)
        self.assertTrue(user2 >= user1)

class TestUserPref(TestCase, CreateUserMixin):

    def test_context(self):
        self.create_users()
        pref = um.UserPref.objects.create(user=self.staff_user)
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
        pref = um.UserPref.objects.create(user=self.staff_user)
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
        form = uf.UserAtomicForm(data=data)
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