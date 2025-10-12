"""
See content.archive for more tests.
Most parts of this app used to be in content.archive, but were moved
to archives app to allow for a more generic backup system.
"""
from django.conf import settings

from base_archives import db_save
from dev.test_utils import TestCase
from dev import test_view, test_data



class TestViews(TestCase, test_data.CreateUserMixin):

    def test_download_db(self):
        url = test_view.TestURL(self, "archives", "download_db", status=403)
        url.test()
        self.create_users()
        url.set_user(self.users[0])
        url.test()
        url.user = self.staff_user
        url.status = 200
        url.data = {
            "db_name": "default"
        }
        url.test()
        db_path = db_save.get_file_path("default")
        self.assertTrue(db_path.exists())
        db_path.unlink()
        self.assertFalse(db_path.exists())
        url.data = {
            "db_name": "non_existing_db"
        }
        url.status = 302
        url.test()