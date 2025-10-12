"""
date: 2025-07-02
"""
import datetime
import subprocess

from django.conf import settings

PARAMS = ["USER", "NAME", "HOST", "PORT"]

def get_file_path(dbname: str) -> str:
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d")
    if not settings.BACKUP_PATH.exists():
        settings.BACKUP_PATH.mkdir(parents=True, exist_ok=True)
    return settings.BACKUP_PATH / f"{dbname}_backup-{timestamp}.sql"

def construct_command(dbname: str) -> list[str]:
    db_settings = settings.DATABASES.get(dbname)
    if not db_settings:
        raise ValueError(f"Database '{dbname}' not found in settings.")
    
    command_template = settings.DB_BACKUP_COMMANDS.get(db_settings['ENGINE'])
    if not command_template:
        raise ValueError(f"No backup command configured for database engine {db_settings['ENGINE']}.")
    
    command_list = [command_template['command']]
    if "base" in command_template:
        command_list.append(command_template['base'])
    for param in PARAMS:
        if param in db_settings and db_settings[param]:
            command_list.append(command_template[param].format(**db_settings))
    FILE = get_file_path(dbname)
    command_list.append(command_template['output'].format(FILE=FILE))
    return " ".join(command_list)

def run_save_command(command: str) -> subprocess.CompletedProcess:
    return subprocess.run(command, shell=True, check=True)

# TODO: implement the restore command
# pg_restore --verbose --clean --no-acl --no-owner -h localhost -U myprojectuser -d myprojectdb {path}