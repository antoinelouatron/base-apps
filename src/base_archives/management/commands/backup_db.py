"""
date: 2025-07-01
"""

import datetime

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

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
            # CommandError, et non un simple message sur stderr : la commande
            # sortait en 0 même après un pg_dump raté, donc le service systemd
            # `Type=oneshot` qui l'appelle chaque nuit concluait au succès. Une
            # base non sauvegardée pendant des semaines sans que rien ne le
            # signale est le pire des scénarios ; il faut un code de retour non
            # nul pour que OnFailure= se déclenche.
            raise CommandError(f"Error during backup: {e}") from e
        else:
            self.stdout.write(self.style.SUCCESS("Database backup completed successfully"))