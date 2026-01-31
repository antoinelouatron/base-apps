import datetime
from pathlib import Path

from django.conf import settings
from django.core.files.uploadedfile import InMemoryUploadedFile

import agenda.forms as af
import agenda.models as am
import agenda.models.cscope as cscope
from dev.test_utils import TestCase
from dev.test_data import TEACHERS, CreateUserMixin
import users.models as um

class TestCscopeTables(TestCase, CreateUserMixin):

    base_dir = settings.TEST_BASE_DIR / "agenda"

    def import_scope(self):
        self.create_students(16)
        self.create_teachers(TEACHERS)
        fpath = self.base_dir / "fixtures" / "colles.csv"
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
            self.assertNotEqual(am.ColleEvent.objects.count(), 0)
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
            data = {"_encoding": "utf8"}
            form = af.CollePlanningImport(data, upl_dict)
            #print(form.errors)
            self.assertTrue(form.is_valid())
            form.save()
            self.assertNotEqual(am.CollePlanning.objects.count(), 0)
    
    def test_table_construction(self):
        self.import_scope()
        level = um.Level.objects.get(name="PT")
        group_table = cscope.GroupDataTable(level)
        group_table.set_week_range(3, 10)
        table = group_table.build_display_table()
        self.assertEqual(len(table.col_names), 8)

        event_table = cscope.EventDataTable(level)
        event_table.set_week_range(3, 10)
        event_table.set_group_range(1, 10)
        table = event_table.build_display_table()
        self.assertEqual(len(table.col_names), 10)
        self.assertEqual(len(table.row_names), 8)