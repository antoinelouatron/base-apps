"""
date: 2025-07-01
"""

from io import StringIO
from django.core.management import call_command
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
        Test the backup_db command with an invalid database name.
        """
        out = StringIO()
        err = StringIO()
        call_command("backup_db", dbname="invalid_db", stdout=out, stderr=err)
        self.assertIn("Error during backup", str(err.getvalue()))