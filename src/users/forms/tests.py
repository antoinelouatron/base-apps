from django.conf import settings
from django.core.files.uploadedfile import InMemoryUploadedFile

import users.forms as cf
import users.models as um
from dev.test_utils import TestCase


class TestImportForms(TestCase):
    """
    Test the import forms for users.
    """

    def test_student_import(self):
        base_path = settings.BASE_DIR / "users" / "fixtures"
        fpath = base_path / "students.csv"
        with open(fpath, "rb") as upl_file:
            data = {
                "_encoding": "utf8",
                "level": -1,
            }
            data.update(cf.StudentImportForm._get_initial_name_mapping())
            files = {
                "import_file": InMemoryUploadedFile(
                        upl_file, None, "students.csv",
                        "text/plain", fpath.stat().st_size, "utf-8"
                    )
            }
            form = cf.StudentImportForm(data, files)
            self.assertFalse(form.is_valid())
        with open(fpath, "rb") as upl_file:
            files = {
                "import_file": InMemoryUploadedFile(
                        upl_file, None, "students.csv",
                        "text/plain", fpath.stat().st_size, "utf-8"
                    )
            }
            level = um.Level.objects.create(name="1ère")
            data["level"] = level.pk
            form = cf.StudentImportForm(data, files)
            self.assertTrue(form.is_valid())
            form.save()
            self.assertEqual(um.User.objects.count(), 20)
    
    def test_student_with_level_import(self):
        base_path = settings.BASE_DIR / "users" / "fixtures"
        fpath = base_path / "students.csv"
        with open(fpath, "rb") as upl_file:
            data = {
                "_encoding": "utf8",
            }
            data.update(cf.StudentWithLevelImportForm._get_initial_name_mapping())
            files = {
                "import_file": InMemoryUploadedFile(
                        upl_file, None, "students.csv",
                        "text/plain", fpath.stat().st_size, "utf-8"
                    )
            }
            form = cf.StudentWithLevelImportForm(data, files)
            # PT might be a valid level, but not PTSI
            self.assertFalse(form.is_valid())
        with open(fpath, "rb") as upl_file:
            pt, _ = um.Level.objects.get_or_create(name="PT")
            ptsi, _ = um.Level.objects.get_or_create(name="PTSI")
            files = {
                "import_file": InMemoryUploadedFile(
                        upl_file, None, "students.csv",
                        "text/plain", fpath.stat().st_size, "utf-8"
                    )
            }
            form = cf.StudentWithLevelImportForm(data, files)
            self.assertTrue(form.is_valid())
            form.save()
            self.assertEqual(um.User.objects.count(), 20)
            # we added student with double level
            self.assertEqual(um.User.objects.students(pt).count(), 11)
            self.assertEqual(um.User.objects.students(ptsi).count(), 11)
            # check colle group creation
            for level in [pt, ptsi]:
                for group_number in range(1, 5):
                    self.assertTrue(
                        um.ColleGroup.objects.filter(
                            level=level,
                            nb=group_number
                        ).exists()
                    )
                    self.assertTrue(
                        um.StudentColleGroup.objects.filter(
                            group__level=level,
                            group__nb=group_number
                        ).exists()
                    )

    def test_idempotence_student_import(self):
        base_path = settings.BASE_DIR / "users" / "fixtures"
        fpath = base_path / "students.csv"
        level = um.Level.objects.create(name="1ère")
        with open(fpath, "rb") as upl_file:
            data = {
                "_encoding": "utf8",
                "level": level.pk,
            }
            data.update(cf.StudentImportForm._get_initial_name_mapping())
            files = {
                "import_file": InMemoryUploadedFile(
                        upl_file, None, "students.csv",
                        "text/plain", fpath.stat().st_size, "utf-8"
                    )
            }
            form = cf.StudentImportForm(data, files)
            self.assertTrue(form.is_valid())
            form.save()
            self.assertEqual(um.User.objects.count(), 20)
            self.assertEqual(um.StudentColleGroup.objects.count(), 20)
        # changer les prénoms puis vérfier que l'import les écrase
        for user in um.User.objects.all():
            self.assertNotEqual(user.first_name, "")
            user.first_name = ""
            user.save()
        with open(fpath, "rb") as upl_file:
            files = {
                "import_file": InMemoryUploadedFile(
                        upl_file, None, "students.csv",
                        "text/plain", fpath.stat().st_size, "utf-8"
                    )
            }
            form = cf.StudentImportForm(data, files)
            self.assertTrue(form.is_valid())
            form.save()
            self.assertEqual(um.User.objects.count(), 20)
            self.assertEqual(um.StudentColleGroup.objects.count(), 20)
            for user in um.User.objects.all():
                self.assertNotEqual(user.first_name, "")
    
    def test_teacher_import(self):
        base_path = settings.BASE_DIR / "users" / "fixtures"
        fpath = base_path / "teachers.csv"
        with open(fpath, "rb") as upl_file:
            data = {
                "_encoding": "utf8",
                "level": -1,
                "subject": -1,
            }
            data.update(cf.TeacherImportForm._get_initial_name_mapping())
            files = {
                "import_file": InMemoryUploadedFile(
                        upl_file, None, "teachers.csv",
                        "text/plain", fpath.stat().st_size, "utf-8"
                    )
            }
            form = cf.TeacherImportForm(data, files)
            self.assertFalse(form.is_valid())
        level = um.Level.objects.create(name="1ère")
        subject = um.Subject.objects.create(name="Math", level=level)
        with open(fpath, "rb") as upl_file:
            files = {
                "import_file": InMemoryUploadedFile(
                        upl_file, None, "teachers.csv",
                        "text/plain", fpath.stat().st_size, "utf-8"
                    )
            }
            data["subject"] = subject.pk
            data["level"] = level.pk
            form = cf.TeacherImportForm(data, files)
            self.assertTrue(form.is_valid())
            form.save()
            self.assertEqual(um.User.objects.count(), 20)
            self.assertEqual(um.User.objects.teachers(subject).count(), 20)
    
    def test_teacher_with_level_import(self):
        base_path = settings.BASE_DIR / "users" / "fixtures"
        fpath = base_path / "teachers.csv"
        with open(fpath, "rb") as upl_file:
            data = {
                "_encoding": "utf8",
            }
            data.update(cf.TeacherForLevelImportForm._get_initial_name_mapping())
            files = {
                "import_file": InMemoryUploadedFile(
                        upl_file, None, "teachers.csv",
                        "text/plain", fpath.stat().st_size, "utf-8"
                    )
            }
            form = cf.TeacherForLevelImportForm(data, files)
            self.assertFalse(form.is_valid())
        with open(fpath, "rb") as upl_file:
            pt, _ = um.Level.objects.get_or_create(name="PT")
            um.Subject.objects.create(name="Math", level=pt)
            um.Subject.objects.create(name="Physique-Chimie", level=pt)
            files = {
                "import_file": InMemoryUploadedFile(
                        upl_file, None, "teachers.csv",
                        "text/plain", fpath.stat().st_size, "utf-8"
                    )
            }
            data["level"] = pt.pk
            form = cf.TeacherForLevelImportForm(data, files)
            self.assertTrue(form.is_valid())
            self.assertEqual(form.cleaned_data["level"], pt)
            self.assertEqual(um.User.objects.count(), 0)
            form.save()
            self.assertEqual(um.User.objects.count(), 20)
            for user in um.User.objects.all():
                self.assertTrue(user.roles.is_teacher(), f"{user} should be a teacher")
            self.assertEqual(um.User.objects.teachers().count(), 20)
    
    def test_teacher_with_subject_import(self):
        base_path = settings.BASE_DIR / "users" / "fixtures"
        fpath = base_path / "teachers.csv"
        
        with open(fpath, "rb") as upl_file:
            data = {
                "_encoding": "utf8",
            }
            data.update(cf.TeacherWithSubjectImportForm._get_initial_name_mapping())
            files = {
                "import_file": InMemoryUploadedFile(
                        upl_file, None, "teachers.csv",
                        "text/plain", fpath.stat().st_size, "utf-8"
                    )
            }
            form = cf.TeacherWithSubjectImportForm(data, files)
            self.assertFalse(form.is_valid())
        levels = [um.Level.objects.get_or_create(name="PT")[0], 
                  um.Level.objects.get_or_create(name="PTSI")[0]]
        subjects = []
        for level in levels:
            subjects.append(um.Subject.objects.create(name="Math", level=level))
            subjects.append(um.Subject.objects.create(name="Physique-Chimie", level=level))
        with open(fpath, "rb") as upl_file:
            files = {
                "import_file": InMemoryUploadedFile(
                        upl_file, None, "teachers.csv",
                        "text/plain", fpath.stat().st_size, "utf-8"
                    )
            }
            form = cf.TeacherWithSubjectImportForm(data, files)
            self.assertTrue(form.is_valid())
            form.save()
            self.assertEqual(um.User.objects.count(), 20)
            for subject in subjects:
                self.assertEqual(um.User.objects.teachers(subject).count(), 5)
    
    def test_colleur_import(self):
        base_path = settings.BASE_DIR / "users" / "fixtures"
        fpath = base_path / "teachers.csv"
        with open(fpath, "rb") as upl_file:
            data = {
                "_encoding": "utf8",
                "level": -1,
                "subject": -1,
            }
            data.update(cf.ColleurImportForm._get_initial_name_mapping())
            files = {
                "import_file": InMemoryUploadedFile(
                        upl_file, None, "teachers.csv",
                        "text/plain", fpath.stat().st_size, "utf-8"
                    )
            }
            form = cf.ColleurImportForm(data, files)
            self.assertFalse(form.is_valid())
        level = um.Level.objects.create(name="1ère")
        subject = um.Subject.objects.create(name="Math", level=level)
        with open(fpath, "rb") as upl_file:
            files = {
                "import_file": InMemoryUploadedFile(
                        upl_file, None, "teachers.csv",
                        "text/plain", fpath.stat().st_size, "utf-8"
                    )
            }
            data["subject"] = subject.pk
            data["level"] = level.pk
            form = cf.ColleurImportForm(data, files)
            self.assertTrue(form.is_valid())
            form.save()
            self.assertEqual(um.User.objects.count(), 20)
            self.assertEqual(um.User.objects.colleurs(subject).count(), 20)

    def test_colleur_with_subject_import(self):
        base_path = settings.BASE_DIR / "users" / "fixtures"
        fpath = base_path / "teachers.csv"
        
        with open(fpath, "rb") as upl_file:
            data = {
                "_encoding": "utf8",
            }
            data.update(cf.ColleurWithSubjectImportForm._get_initial_name_mapping())
            files = {
                "import_file": InMemoryUploadedFile(
                        upl_file, None, "teachers.csv",
                        "text/plain", fpath.stat().st_size, "utf-8"
                    )
            }
            form = cf.ColleurWithSubjectImportForm(data, files)
            self.assertFalse(form.is_valid())
        levels = [um.Level.objects.get_or_create(name="PT")[0], 
                  um.Level.objects.get_or_create(name="PTSI")[0]]
        subjects = []
        for level in levels:
            subjects.append(um.Subject.objects.create(name="Math", level=level))
            subjects.append(um.Subject.objects.create(name="Physique-Chimie", level=level))
        with open(fpath, "rb") as upl_file:
            files = {
                "import_file": InMemoryUploadedFile(
                        upl_file, None, "teachers.csv",
                        "text/plain", fpath.stat().st_size, "utf-8"
                    )
            }
            form = cf.ColleurWithSubjectImportForm(data, files)
            self.assertTrue(form.is_valid())
            form.save()
            self.assertEqual(um.User.objects.count(), 20)
            for subject in subjects:
                self.assertEqual(um.User.objects.colleurs(subject).count(), 5)