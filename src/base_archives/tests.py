"""
See content.archive for more tests.
Most parts of this app used to be in content.archive, but were moved
to archives app to allow for a more generic backup system.
"""
from django.conf import settings

from base_archives import db_save
from dev.test_utils import TestCase
from dev import test_view, test_data


class TestExplicitPath(TestCase):
    """
    Destination imposée par le consommateur (`path`), pour une sauvegarde qui
    doit survivre à la rotation des sauvegardes courantes.
    """

    def test_default_path_unchanged(self):
        self.assertEqual(
            db_save.get_file_path("default"),
            settings.BACKUP_PATH / db_save.get_file_path("default").name)
        self.assertEqual(
            db_save.get_file_path("default").parent, settings.BACKUP_PATH)

    def test_explicit_path_creates_parent(self):
        target = settings.BACKUP_PATH / "sous-dossier" / "archive.dump"
        self.assertFalse(target.parent.exists())
        path = db_save.get_file_path("default", target)
        self.assertEqual(path, target)
        self.assertTrue(target.parent.is_dir())
        target.parent.rmdir()

    def test_explicit_path_out_of_rotation_glob(self):
        """
        Un sous-dossier échappe au ménage de `backup_db` : son glob est
        `BACKUP_PATH/*.sql`, non récursif.
        """
        target = settings.BACKUP_PATH / "cloture" / "2025-2026.dump"
        db_save.get_file_path("default", target)
        target.write_bytes(b"")
        self.assertNotIn(target, list(settings.BACKUP_PATH.glob("*.sql")))
        target.unlink()
        target.parent.rmdir()

    def test_command_targets_explicit_path(self):
        target = settings.BACKUP_PATH / "cloture" / "2025-2026.dump"
        command = db_save.construct_command("default", target)
        self.assertIn(str(target), command)
        self.assertNotIn(str(db_save.get_file_path("default")), command)
        target.parent.rmdir()


class TestViews(TestCase, test_data.CreateUserMixin):

    def test_download_db(self):
        url = test_view.TestURL(self, "archives", "download_db", status=403)
        url.test()
        self.create_users()
        url.set_user(self.users[0])
        url.test()
        # gating générique : seul un superutilisateur passe (cf. settings de test
        # ARCHIVES_DOWNLOAD_PERMISSION = utils.permissions.SUPERUSER).
        url.user = self.admin_user
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