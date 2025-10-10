import datetime
from django.conf import settings
from django.core.files.uploadedfile import InMemoryUploadedFile

import agenda.forms as af
import agenda.models as am
from agenda.forms.tests import create_subjects
from dev.test_data import CreateUserMixin
from dev.test_utils import TestCase
from dev.test_view import TestURL
import users.change_collegroups as uc
import users.models as um


class LoadAllData(TestCase, CreateUserMixin):

    def setUp(self):
        self.create_users()
        return super().setUp()

    def load_users(self):
        base_path = settings.BASE_DIR / "users" / "fixtures"
        url = TestURL(self, "import", "users", status=302)
        url.set_user(self.staff_user)
        fpath = base_path / "teachers.json"
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
            url.test()
        url = TestURL(self, "import", "users", status=302)
        url.set_user(self.staff_user)
        fpath = base_path / "etudiants-pt.csv"
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
            url.test()
    
    def load_EDT(self):
        fpath = settings.BASE_DIR / "agenda" / "fixtures" / "edt.json"
        self.assertTrue(fpath.exists())
        level = um.get_default_level(instance=True)
        create_subjects(level)
        with open(fpath, "rb") as upl_file:
            upl_dict = {"import_file": InMemoryUploadedFile(
                upl_file, None, "edt.json",
                "text/plain", fpath.stat().st_size, "utf-8"
            )}
            data = {
                "_encoding": "utf8",
                "_name_mapping_9": "attendance",
                "level": level.id
            }
            form = af.PeriodicImport(data, upl_dict)
            self.assertTrue(form.is_valid())
            form.save()
    
    def load_colles(self, planning=True):
        fpath = settings.BASE_DIR / "agenda" / "fixtures" / "colles.csv"
        self.assertTrue(fpath.exists())
        with open(fpath, "rb") as upl_file:
            upl_dict = {"import_file": InMemoryUploadedFile(
                upl_file, None, "colles.csv",
                "text/plain", fpath.stat().st_size, "utf-8"
            )}
            data = {"_encoding": "utf8"}
            form = af.ColleEventImport(data, upl_dict)
            self.assertTrue(form.is_valid())
            form.save()
        fpath = settings.BASE_DIR / "agenda" / "fixtures" / "scope-pt.csv"
        if not planning:
            return
        for nb in range(3, 26):
            am.Week.objects.create(nb=nb,
                begin=datetime.date.today() + datetime.timedelta(7*(nb-3)),
                end=datetime.date.today() + datetime.timedelta(7*(nb-2)),
                active=True)
        self.assertTrue(fpath.exists())
        with open(fpath, "rb") as upl_file:
            upl_dict = {"import_file": InMemoryUploadedFile(
                upl_file, None, "scope-pt.csv",
                "text/plain", fpath.stat().st_size, "utf-8"
            )}
            data = {"_encoding": "utf8"}
            form = af.CollePlanningImport(data, upl_dict)
            self.assertTrue(form.is_valid())
            form.save()

    def load_all(self, planning=True):
        self.load_users()
        self.assertEqual(um.User.objects.count(), 3 + 11 + 34)
        self.load_EDT()
        self.assertEqual(am.PeriodicEvent.objects.count(), 49)
        self.load_colles(planning=planning)
        self.assertEqual(am.ColleEvent.objects.count(), 28)
        if planning:
            self.assertEqual(am.CollePlanning.objects.count(), 528)

class TestChangeAtt(LoadAllData):

    def test_fixtures(self):
        self.load_all()
    
    def management_data(self, count):
        # see test_fixtures to check form number
        form_nb = count
        return {
            "form-TOTAL_FORMS": form_nb,
            "form-INITIAL_FORMS": form_nb,
            "form-MIN_NUM_FORMS": 0,
            "form-MAX_NUM_FORMS": 1000,
        }
    
    def test_formset(self):
        self.load_all(planning=False)
        change_att = uc.ChangeAttendance()
        fset = change_att.get_formset()
        count = um.ColleGroup.objects.count()
        self.assertEqual(len(fset.forms), count)
        data = {"form-{}-nb".format(i): (i % 3) for i in range(len(fset.forms))}
        data.update(self.management_data(count))
        fset = change_att.get_formset(data=data)
        self.assertFalse(fset.is_valid(), fset.errors)
    
    def test_change_att(self):
        self.load_all()
        # we introduce incoherence with a void group, since timetable is not
        # updated with 13th group, we should not have any problem
        void_group = um.ColleGroup.objects.create(nb=13, void=True)
        group_nb = 13
        change_att = uc.ChangeAttendance()
        group = um.ColleGroup.objects.get(nb=1)
        group2 = um.ColleGroup.objects.get(nb=8)
        groups = list(um.ColleGroup.objects.order_by("nb"))
        td2 = am.PeriodicEvent.objects.get(
            beghour="14:00",
            subject="math",
            begweek=0
        )
        td = am.PeriodicEvent.objects.get(
            beghour="14:00",
            subject="math",
            begweek=1
        )
        attendants = set(td.attendants.all())
        attendants2 = set(td2.attendants.all())
        teachers = set(td.attendants.filter(teacher=True))
        teachers2 = set(td2.attendants.filter(teacher=True))
        for scg in group.studentcollegroup_set.all():
            self.assertIn(scg.user, attendants)
            self.assertNotIn(scg.user, attendants2)
        for t in teachers:
            self.assertIn(t, attendants)
        for t in teachers2:
            self.assertIn(t, attendants2)

        
        data = self.management_data(group_nb)
        # there should be 14 groups
        self.assertEqual(len(change_att.groups), group_nb)
        for i in range(group_nb):
            data["form-{}-nb".format(i)] = 1 + ((group_nb//2 + i) % group_nb)
            data["form-{}-id".format(i)] = groups[i].pk
        fset = change_att.get_formset(data=data)
        self.assertTrue(fset.is_valid(), fset.errors + [fset.non_form_errors()])
        old_studs1 = set(group.students())
        old_studs8 = set(group2.students())
        instances = fset.save()
        change_att.update_attendance(instances)

        group = um.ColleGroup.objects.get(nb=1)
        group2 = um.ColleGroup.objects.get(nb=7)
        self.assertEqual(old_studs1, set(group2.students()))
        self.assertEqual(old_studs8, set(group.students()))
        void_group.refresh_from_db()
        self.assertFalse(void_group.void)
        new_void = um.ColleGroup.objects.get(nb=6) # with group_nb == 13
        self.assertTrue(new_void.void)

        td = am.PeriodicEvent.objects.get(pk=td.pk)
        td2 = am.PeriodicEvent.objects.get(pk=td2.pk)
        attendants = set(td.attendants.all())
        attendants2 = set(td2.attendants.all())
        for stud in um.User.objects.filter(pk__in=old_studs1):
            self.assertNotIn(stud, attendants)
            self.assertIn(stud, attendants2)
        for t in teachers:
            self.assertIn(t, attendants)
        for t in teachers2:
            self.assertIn(t, attendants2)
    
    def test_view(self):
        self.load_all()
        url = TestURL(self, "users", "change_collegroups", status=403)
        url.test()
        url.set_user(self.users[0])
        url.test()
        url.status = 200
        self.staff_user.teacher = True
        self.staff_user.save()
        url.set_user(self.staff_user)
        url.test()
        url.method = "post"
        group_nb = 12
        groups = list(um.ColleGroup.objects.order_by("nb"))
        data = self.management_data(group_nb)
        for i in range(group_nb):
            data["form-{}-nb".format(i)] = 1 + ((group_nb//2 + i) % group_nb)
            data["form-{}-id".format(i)] = groups[i].pk
        data["form-{}-nb".format(0)] = 13
        url.data = data
        url.status = 200
        resp = url.test()
        self.assertIn("form", resp.context)
        self.assertFalse(resp.context["form"].is_valid())
        data["form-{}-nb".format(0)] = 7
        url.data = data
        url.status = 302
        url.test()
        # test failure in case of tempered attendance
        ev = am.PeriodicEvent.objects.last()
        ev._attendance_string = "M. Unknown,1-12"
        ev.save()
        url.status = 200
        resp = url.test()
        self.assertIn("form", resp.context)
        self.assertFalse(resp.context["form"].is_valid())



        

