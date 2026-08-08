"""
date: 2025-07-02
"""
import datetime
import shlex
import subprocess

from pathlib import Path

from django.conf import settings

PARAMS = ["USER", "NAME", "HOST", "PORT"]

def get_file_path(dbname: str, path: Path|None=None) -> Path:
    """
    Chemin du fichier de sauvegarde.

    `path` permet au consommateur d'imposer sa destination, pour une sauvegarde
    qui ne doit pas suivre le sort des sauvegardes courantes : celles-ci sont
    datées et effacées au bout de 60 jours par `backup_db.clean_old_backups`,
    dont le glob (`BACKUP_PATH/*.sql`) ne descend pas dans les sous-dossiers.
    Le dossier parent est créé au besoin, comme pour la destination par défaut.
    """
    if path is not None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        return path
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d")
    if not settings.BACKUP_PATH.exists():
        settings.BACKUP_PATH.mkdir(parents=True, exist_ok=True)
    return settings.BACKUP_PATH / f"{dbname}_backup-{timestamp}.sql"

def construct_command(dbname: str, path: Path|None=None) -> list[str]:
    db_settings = settings.DATABASES.get(dbname)
    if not db_settings:
        raise ValueError(f"Database '{dbname}' not found in settings.")

    command_template = settings.DB_BACKUP_COMMANDS.get(db_settings['ENGINE'])
    if not command_template:
        raise ValueError(f"No backup command configured for database engine {db_settings['ENGINE']}.")

    # Build an argv list (no shell) : each template fragment is tokenized with
    # shlex, then each token is formatted individually so substituted values
    # (USER, HOST, FILE, ...) always land in their own argument and can never
    # be re-split or interpreted by a shell.
    command_list = [command_template['command']]
    if "base" in command_template:
        command_list.extend(shlex.split(command_template['base']))
    for param in PARAMS:
        if param in db_settings and db_settings[param]:
            command_list.extend(
                tok.format(**db_settings) for tok in shlex.split(command_template[param]))
    FILE = get_file_path(dbname, path)
    command_list.extend(
        tok.format(FILE=FILE) for tok in shlex.split(command_template['output']))
    return command_list

def run_save_command(command: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(command, shell=False, check=True)

# TODO: implement the restore command
# pg_restore --verbose --clean --no-acl --no-owner -h localhost -U myprojectuser -d myprojectdb {path}