from pathlib import Path

from bs4 import BeautifulSoup
from django.core import mail
from django.core.files.uploadedfile import InMemoryUploadedFile


from dev.test_data import CreateUserMixin
from dev.test_view import TestURL, TestCase, JsonURL
from users.models import User, ColleGroup

class SeeAsViewTest(TestCase):
    @classmethod
    def setUpClass(self):
        super().setUpClass()
        self.user = User.objects.create_user(username='testuser', password='testpassword')
        self.teacher = User.objects.create_teacher(username='teacher', password='teacherpassword')

    def test_view_with_teacher_user(self):
        url = TestURL(self, "users", "see_as", user=self.teacher)
        url.test()
        #self.assertTemplateUsed(response, 'users/see_as.html')
        #self.assertContains(response, 'Espionnage')

    def test_view_with_non_teacher_user(self):
        #self.client.login(username='testuser', password='testpassword')
        url = TestURL(self, "users", "see_as", user=self.user, status=403)
        url.test()

    def test_view_with_staff(self):
        self.user.is_staff = True
        self.user.save()
        url = TestURL(self, "users", "see_as", user=self.user)
        url.test()
        self.user.is_staff = False
        self.user.save()
        #self.assertTemplateUsed(response, 'users/see_as.html')
        #self.assertContains(response, 'Espionnage')

    def test_get_referer(self):
        url = TestURL(self, "users", "see_as", user=self.teacher)
        response = url.test(HTTP_REFERER='/?param=1')
        #self.assertTemplateUsed(response, 'users/see_as.html')
        #self.assertContains(response, 'Espionnage')
        self.assertEqual(response.context["referer"], "/?param=1&")
        resp = url.test(HTTP_REFERER=f"/?see_as={self.teacher.pk}")
        self.assertEqual(resp.context["referer"], "/?")
        resp = url.test(HTTP_REFERER="/?reset_user=1")
        self.assertEqual(resp.context["referer"], "/?")
        resp = url.test(HTTP_REFERER=f"/?see_as={self.teacher.pk}&param=1")
        self.assertEqual(resp.context["referer"], "/?param=1&")
        resp = url.test(HTTP_REFERER=f"/?see_as={self.teacher.pk}&reset_user=1")
        self.assertEqual(resp.context["referer"], "/?")
        resp = url.test(HTTP_REFERER=f"/?see_as={self.teacher.pk}&param=1&reset_user=1")
        self.assertEqual(resp.context["referer"], "/?param=1&")
    
    def test_get_queryset(self):
        url = TestURL(self, "users", "see_as", user=self.teacher)
        self.user.is_staff = True
        self.user.save()
        response = url.test()
        self.assertEqual(response.context['object_list'].count(), 1)
        self.user.is_staff = False
        self.user.save()
        response = url.test()
        self.assertEqual(response.context['object_list'].count(), 2)
        superuser = User.objects.create_superuser(username='superuser',
            password='superpassword')
        url.user = superuser
        response = url.test()
        self.assertEqual(response.context['object_list'].count(), 3)
    
    def test_middleware(self):
        url = TestURL(self, "", "account_login", user=self.user)
        url.data = {"see_as": self.teacher.pk}
        resp = url.test()
        self.assertIn("request", resp.context, "request in context")
        request = resp.context["request"]
        self.assertEqual(request.user, self.user)
        self.assertIsNone(request.session.get("see_as", None))
        url.user = self.teacher
        url.data = {"see_as": self.user.pk}
        resp = url.test()
        self.assertIn("request", resp.context, "request in context")
        self.assertEqual(resp.context["request"].user, self.user)
        self.assertEqual(resp.context["request"].session["see_as"], str(self.user.pk))
        url.data = {"reset_user": "1"}
        resp = url.test()
        self.assertEqual(resp.context["request"].user, self.teacher)
        self.assertIsNone(resp.context["request"].session.get("see_as", None))
        url.data = {"see_as": "-1"}
        resp = url.test()
        self.assertFalse(resp.context["request"].user.is_authenticated)

class TestImportUsers(TestCase, CreateUserMixin):
    def setUp(self):
        self.create_users()
    
    def test_import_users(self):
        self.assertEqual(User.objects.count(), 3)
        url = TestURL(self, "import", "users", status=403)
        url.test()
        url.set_user(self.staff_user)
        url.status = 200
        url.test()
        fpath = Path(__file__).parent / "fixtures" / "teachers.json"
        with open(fpath, "rb") as upl_file:
            url.data = {
                "_encoding": "utf8",
                "_name_mapping_2": "title",
                "teacher": True,
                "import_file": InMemoryUploadedFile(
                    upl_file, None, "teachers.json",
                    "text/plain", fpath.stat().st_size, "utf-8"
                )
            }
            # redirect
            url.method = "post"
            resp = url.test(follow=True)
            ctx = resp.context
            messages = list(ctx["messages"])
            messages = [m.message for m in messages]
            self.assertIn("11 créé(s)", messages)
            self.assertEqual(User.objects.count(), 14, "11 more")
    
    def test_import_students(self):
        self.assertEqual(User.objects.filter(student=True).count(), 0)
        url = TestURL(self, "import", "users", status=403)
        url.test()
        url.set_user(self.staff_user)
        url.status = 200
        url.test()
        fpath = Path(__file__).parent / "fixtures" / "etudiants-pt.csv"
        with open(fpath, "rb") as upl_file:
            url.data = {
                "_encoding": "utf8",
                "teacher": False,
                "student": True,
                "import_file": InMemoryUploadedFile(
                    upl_file, None, "etudiants-pt.csv",
                    "text/plain", fpath.stat().st_size, "utf-8"
                )
            }
            # redirect
            url.method = "post"
            resp = url.test(follow=True)
            ctx = resp.context
            messages = list(ctx["messages"])
            messages = [m.message for m in messages]
            self.assertIn("34 créé(s)", messages)
            self.assertEqual(User.objects.count(), 37, "34 more")
            self.assertEqual(ColleGroup.objects.count(), 12, "12 groups")


class TestBaseAccess(TestCase, CreateUserMixin):
    def setUp(self):
        self.create_users()
    
    def test_base_access(self):
        url = TestURL(self, "users", "account", status=403)
        url.test()
        url.method = "post"
        url.test()
        url.method = "get"
        student = self.create_students(1)[0]
        url.set_user(student)
        url.status = 200
        url.test()
        self.staff_user.teacher = True
        self.staff_user.save()
        url.set_user(self.staff_user)
        url.status = 200
        url.test()
        # self.assertNotIn("config_form", resp.context)
        # self.users[0].student = True
        # url.set_user(self.users[0])
        # url.status = 200
        # resp = url.test()
        # self.assertNotIn("config_form", resp.context)
        # url.set_user(self.staff_user)
        # self.staff_user.is_superuser = True
        # self.staff_user.save()
        # url.status = 200
        # resp = url.test()
        # self.assertIn("config_form", resp.context)
        # url.method = "post"
        # url.status = 302
        # url.data = {
        #     "inscription": True,
        # }
        # url.test()
        # url.status = 200
        # resp = url.test(follow=True)
        # import content.models.base as cb
        # config = cb.ContentConfig.instance.get()
        # self.assertTrue(config.inscription)
        # url.set_user(self.users[0])
        # url.status = 405
        # url.test()
    
    def test_user_list(self):
        url = JsonURL(self, "users", "list", status=403)
        url.test(forbidden=True)
        url.set_user(self.users[0])
        url.status = 200
        resp = url.test()
        data = resp.json()
        self.assertEqual(len(data), 2, "status, users")
        self.create_students(4)
        resp = url.test()
        data = resp.json()
        self.assertIn("users", data)
        self.assertEqual(len(data["users"]), 4, "4 groups, 1 user by group")
        for g in data["users"]:
            self.assertEqual(len(g), 1, "1 user by group")
    
    def test_collegroups_list(self):
        url = TestURL(self, "users", "collegroups", status=403)
        url.test()
        url.set_user(self.users[0])
        url.test()
        self.staff_user.teacher = True
        self.staff_user.save()
        url.set_user(self.staff_user)
        url.status = 200
        resp = url.test()
        self.assertIn("object_list", resp.context)
        self.assertEqual(len(resp.context["object_list"]), 0)
        student = self.create_students(1)[0]
        url.set_user(student)
        url.status = 403
        url.test()


class TestLogin(TestCase, CreateUserMixin):
    def setUp(self):
        self.create_users()
    
    def test_login(self):
        url = TestURL(self, "", "account_login", status=200)
        resp = url.test(skip_title=True)
        self.assertIn("form", resp.context)
        url.method = "post"
        url.data = {
            "username": self.users[0].username,
            "password": "wrongpassword"
        }
        url.status = 200
        resp = url.test(skip_title=True)
        self.assertIn("form", resp.context)
        self.assertFalse(resp.context["form"].is_valid())
        self.users[0].set_password("password")
        self.users[0].save()
        url.data = {
            "username": self.users[0].username,
            "password": "password"
        }
        resp = url.test(skip_title=True, follow=True)
        self.assertIn("request", resp.context)
        self.assertEqual(resp.context["request"].user, self.users[0])
    
    def test_logout(self):
        url = TestURL(self, "", "account_logout", status=405)
        url.set_user(self.users[0])
        resp = url.test(skip_title=True)
        # no logout on GET
        #self.assertTrue(resp.context["request"].user.is_authenticated)
        url.method = "post"
        url.data = {
            "logout": "Logout"
        }
        url.status = 200
        resp = url.test(skip_title=True, follow=True)
        self.assertIn("request", resp.context)
        self.assertFalse(resp.context["request"].user.is_authenticated)
    
    def test_send_mail(self):
        mail.send_mail(
            "Subject here",
            "Here is the message.",
            "from@example.com",
            ["to@example.com"],
            fail_silently=False,
        )

        # Test that one message has been sent.
        self.assertEqual(len(mail.outbox), 1)

        # Verify that the subject of the first message is correct.
        self.assertEqual(mail.outbox[0].subject, "Subject here")
    
    def _parse_reset_mail(self, mail_body):
        soup = BeautifulSoup(mail_body, "lxml")
        link = soup.find("a", string="Réinitialiser mon mot de passe")
        href = link["href"]
        parts = href.split("/")
        uidb64 = parts[-3]
        token = parts[-2]
        return uidb64, token
    
    def test_reset_password(self):
        url = TestURL(self, "", "account_reset_password", status=200)
        resp = url.test(skip_title=True)
        self.assertIn("form", resp.context)
        url.method = "post"
        url.data = {
            "email": "user@example.com"
        }
        url.status = 200
        resp = url.test(skip_title=True, follow=True)
        self.assertEqual(len(mail.outbox), 0)
        self.users[0].is_active = True
        # require usable password !
        self.users[0].set_password("password")
        self.users[0].email = "user@example.com"
        self.users[0].save()
        resp = url.test(skip_title=True, follow=True)
        self.assertEqual(len(mail.outbox), 1)
        sent = mail.outbox[0]
        uid, token = self._parse_reset_mail(sent.body)
        # PasswordResetConfirmView makes a redirection if the token is valid
        # to avoid leaking the token in Referer header
        url = TestURL(self, "", "password_reset_confirm",
            kwargs={"uidb64": uid, "token": token}, status=200)
        resp = url.test(follow=True)
        self.assertIn("form", resp.context)