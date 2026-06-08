"""
date: 2024-04-10
"""
import datetime
from pathlib import Path

from django.conf import settings
from django.core.files.uploadedfile import InMemoryUploadedFile

import agenda.forms as af
import agenda.models as am
from dev.test_utils import TestCase
from dev.test_data import CreateUserMixin, TEACHERS
import users.models as um

class TestPeriodicForm(TestCase, CreateUserMixin):

    def test_attendance_string(self):
        
        level = um.Level.objects.create(name="3e")
        self.create_students(3, level=level)
        subject = am.Subject.objects.create(name="math", level=level)
        data = {
            "begweek": 0,
            "endweek": 35,
            "beghour": "8:0:0",
            "endhour": "10:0:0",
            "periodicity": 2,
            "day": 3,
            "label": "test",
            "subj": subject.id,
            "_attendance_string": "1-3"
        }
        form = af.PeriodicForm(data=data)
        self.assertTrue(form.is_valid())
        inst = form.save()
        self.assertEqual(inst.attendants.count(), 3)
        form = af.PeriodicForm(data=data)
        self.assertTrue(form.is_valid())
        inst = form.save(commit=False)
        inst.save()
        self.assertEqual(inst.attendants.count(), 0)
        form.save_m2m()
        self.assertEqual(inst.attendants.count(), 3)
        self.assertEqual(am.PeriodicEvent.objects.count(), 2)
    
    def test_time_formats(self):
        level = um.Level.objects.create(name="3e")
        subject = am.Subject.objects.create(name="math", level=level)
        data = {
            "begweek": 0,
            "endweek": 35,
            "beghour": "8:0:0",
            "endhour": "10:0:0",
            "periodicity": 2,
            "day": 3,
            "label": "test",
            "subj": subject.id,
            "_attendance_string": "1-3"
        }
        form = af.PeriodicForm(data=data)
        self.assertTrue(form.is_valid())
        data["beghour"] = "8:0"
        form = af.PeriodicForm(data=data)
        self.assertTrue(form.is_valid())
    
    def test_non_existing_teacher(self):
        self.assertEqual(um.User.objects.teachers().filter(is_active=True).count(), 0)
        data = {
            "begweek": 0,
            "endweek": 35,
            "beghour": "8:0:0",
            "endhour": "10:0:0",
            "periodicity": 2,
            "day": 3,
            "label": "test",
            "subject": "math",
            "_attendance_string": "M. Unknown,1-3",
        }
        form = af.PeriodicForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("_attendance_string", form.errors)
        self.assertEqual(am.PeriodicEvent.objects.count(), 0)

def create_subjects(level):
    # see fixture file
    subjects_names = ["math", "physique", "francais", "anglais",
        "TIPE", "SI", "info", "sii", "informatique", "Mathématiques",
        "français"]
    subjects = []
    for name in subjects_names:
        subj, _ = am.Subject.objects.get_or_create(name=name, level=level)
        subjects.append(subj)
    return subjects

class TestImportForms(TestCase, CreateUserMixin):

    base_dir = settings.TEST_BASE_DIR / "agenda"

    def setUp(self):
        #self.create_students(16)
        self.level = um.Level.objects.create(name="3e")
        self.create_teachers(TEACHERS, level=self.level)
        self.subjs = create_subjects(self.level)
        for t in self.teachers:
            t.roles.add(um.AtomicRole.create(teacher=True, subject=self.subjs[0]))
            t.save()
    
    def test_import_edt(self):
        fpath = self.base_dir / "fixtures" / "edt.json"
        self.assertTrue(fpath.exists())
        level = self.level
        self.create_students(16, level=level)
        with open(fpath, "rb") as upl_file:
            upl_dict = {
                "import_file": InMemoryUploadedFile(
                    upl_file, None, "edt.json",
                    "text/plain", fpath.stat().st_size, "utf-8"
                )
            }
            data = {
                "_encoding": "utf8",
                #"_name_mapping_9": "attendance",
                #"level": level.id
            }
            form = af.PeriodicImport(data, upl_dict)
            self.assertFalse(form.is_valid())
        with open(fpath, "rb") as upl_file:
            #create_subjects(level)
            # file is consumed !
            upl_dict = {
                "import_file": InMemoryUploadedFile(
                    upl_file, None, "edt.json",
                    "text/plain", fpath.stat().st_size, "utf-8"
                )
            }
            data = {
                "_encoding": "utf8",
                "_name_mapping_9": "attendance",
                "level": level.id
            }
            form = af.PeriodicImport(data, upl_dict)
            self.assertTrue(form.is_valid())
            # test auto_complete
            nm = form.cleaned_data["_name_mapping"]
            self.assertEqual(nm["attendance"], "_attendance_string")
            self.assertEqual(len(nm), 10)
            self.assertTrue(form.is_valid())
            instances = form.save(commit=False)
            self.assertEqual(am.PeriodicEvent.objects.count(), 0)
            for inst in instances:
                inst.save()
                self.assertEqual(inst.attendants.count(), 0)
            form.save_m2m()
            for inst in instances:
                inst.save()
                self.assertTrue(inst.attendants.count() > 1)
    
    def test_import_colle_events(self):
        self.create_students(16, level=self.level)
        fpath = self.base_dir / "fixtures" / "colles.csv"
        self.assertTrue(fpath.exists())
        self.assertEqual(um.User.objects.colleurs().count(), 0)
        with open(fpath, "rb") as upl_file:
            upl_dict = {"import_file": InMemoryUploadedFile(
                upl_file, None, "colles.csv",
                "text/plain", fpath.stat().st_size, "utf-8"
            )}
            data = {"_encoding": "utf8", "level": self.level.id}
            form = af.ColleEventImport(data, upl_dict)
            self.assertTrue(form.is_valid())
            form.save()
            self.assertNotEqual(am.ColleEvent.objects.count(), 0)
            self.assertEqual(um.User.objects.colleurs().count(), 20)
        for nb in range(3, 26):
            am.Week.objects.create(nb=nb,
                begin=datetime.date.today() + datetime.timedelta(7*(nb-3)),
                end=datetime.date.today() + datetime.timedelta(7*(nb-2)),
                active=True)
        fpath = Path(__file__).parent / ".." / "fixtures" / "scope-pt.csv"
        self.assertTrue(fpath.exists())
        with open(fpath, "rb") as upl_file:
            upl_dict = {"import_file": InMemoryUploadedFile(
                upl_file, None, "scope-pt.csv",
                "text/plain", fpath.stat().st_size, "utf-8"
            )}
            data = {"_encoding": "utf8", "level": self.level.id}
            form = af.CollePlanningImport(data, upl_dict)
            self.assertTrue(form.is_valid())
            form.save()
            self.assertNotEqual(am.CollePlanning.objects.count(), 0)
    
    def test_colle_planning_cleaning(self):
        self.create_students(16)
        data = {
            "week": 3,
            "event": "test",
            "group": 1
        }
        form = af.CollePlanningAtomic(
            data=data, weeks=[], events=[], groups=[])
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 3)
        form = af.CollePlanningAtomic(data=data, weeks=am.Week.objects.all(),
                                      events=am.ColleEvent.objects.all(),
                                      groups=um.ColleGroup.objects.all())
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 2)
        nb = 3
        am.Week.objects.create(nb=nb,
                begin=datetime.date.today() + datetime.timedelta(7*(nb-3)),
                end=datetime.date.today() + datetime.timedelta(7*(nb-2)))
        form = af.CollePlanningAtomic(data=data, weeks=am.Week.objects.all(),
                                      events=am.ColleEvent.objects.all(),
                                      groups=um.ColleGroup.objects.all())
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        event = am.ColleEvent.objects.create(
            beghour=datetime.time(8, 0, 0),
            endhour=datetime.time(10, 0, 0),
            day=3, subject="test", abbrev="test",
            teacher=um.User.objects.first())
        form = af.CollePlanningAtomic(data=data, weeks=am.Week.objects.all(),
                                      events=am.ColleEvent.objects.all(),
                                      groups=um.ColleGroup.objects.all())
        form.is_valid()
        self.assertTrue(form.is_valid())

class TestToDoForm(TestCase, CreateUserMixin):

    def setUp(self):
        self.level = um.Level.objects.create(name="testlevel")

    def test_attendance_string(self):
        self.create_students(3)
        data = {
            "date": datetime.date.today(),
            "label": "test",
            "long_label": "test",
            "_attendance_string": "1-3",
            "msg_level": 1
        }
        form = af.ToDoForm(data=data)
        self.assertTrue(form.is_valid())
        inst = form.save()
        self.assertEqual(inst.attendants.count(), 3)
        form = af.ToDoForm(data=data)
        self.assertTrue(form.is_valid())
        inst = form.save(commit=False)
        inst.save()
        form.save_m2m()
        self.assertEqual(inst.attendants.count(), 3)
        self.assertEqual(am.ToDo.objects.count(), 2)
    
    def test_student_field(self):
        self.create_users(3)
        self.create_students(3, level=self.level)
        data = {
            "date": datetime.date.today(),
            "label": "test",
            "long_label": "test",
            "students": True,
            "msg_level": 1
        }
        form = af.ToDoForm(data=data, level=self.level)
        self.assertTrue(form.is_valid())
        inst = form.save()
        self.assertEqual(inst.attendants.count(), 3)
    
    def test_all_field(self):
        self.create_users(3)
        self.create_students(3)
        data = {
            "date": datetime.date.today(),
            "label": "test",
            "long_label": "test",
            "all": True,
            "msg_level": 1
        }
        form = af.ToDoForm(data=data)
        self.assertTrue(form.is_valid())
        inst = form.save()
        self.assertEqual(inst.attendants.count(), 8, "staff, admin, 3 users, 3 students")
        data["students"] = True
        form = af.ToDoForm(data=data)
        self.assertTrue(form.is_valid())
        inst = form.save()
        self.assertEqual(inst.attendants.count(), 8)
        self.assertEqual(am.ToDo.objects.count(), 2)
