"""
date: 2025-07-01
"""

import datetime

from django.conf import settings
from django.core.management.base import BaseCommand

from base_archives import db_save

class Command(BaseCommand):
    help = "Backup the database"
    PARAMS = ["USER", "NAME", "HOST", "PORT"]

    def add_arguments(self, parser):
        parser.add_argument(
            '--dbname',
            type=str,
            help='The setting name of the database to backup',
            default="default"
        )

    def clean_old_backups(self):
        backup_path = settings.BACKUP_PATH
        for file in backup_path.glob("*.sql"):
            if file.stat().st_mtime < (datetime.datetime.now() - datetime.timedelta(days=60)).timestamp():
                file.unlink()
                self.stdout.write(f"Deleted old backup: {file.name}")

    def handle(self, *args, **options):
        dbname = options.get("dbname", "default")
        self.stdout.write(f"Starting backup for database: {dbname}")

        try:
            command = db_save.construct_command(dbname)
            self.stdout.write(f"Executing backup command: {command}")
            # Execute the backup command
            db_save.run_save_command(command)
            # clean up old backups
            self.clean_old_backups()
        except Exception as e:
            self.stderr.write(f"Error during backup: {e}")
        else:
            self.stdout.write(self.style.SUCCESS("Database backup completed successfully"))