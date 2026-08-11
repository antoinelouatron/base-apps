"""
date: 2025-07-01
"""

from io import StringIO
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import tag

from base_archives import db_save
from dev.test_utils import TestCase

class TestBackupDBCommand(TestCase):
    """
    Test the backup_db command.
    """
    @tag("backup-db")
    def test_backup_command(self):
        """
        Test the backup_db command.
        """
        out = StringIO()
        call_command("backup_db", stdout=out)
        self.assertIn("Database backup completed successfully", str(out.getvalue()))
        # Check if the backup file was created
        path = db_save.get_file_path("default")
        self.assertTrue(path.exists(), f"Backup file {path} was not created.")
    
    @tag("backup-db")
    def test_option_and_fail(self):
        """
        Un échec doit sortir en erreur, pas seulement écrire sur stderr : le
        service systemd qui appelle cette commande chaque nuit est un
        Type=oneshot, et un code de retour 0 lui fait conclure au succès.
        """
        out = StringIO()
        with self.assertRaises(CommandError) as ctx:
            call_command("backup_db", dbname="invalid_db", stdout=out)
        self.assertIn("Error during backup", str(ctx.exception))