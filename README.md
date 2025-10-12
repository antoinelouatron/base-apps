## Installation
Utiliser poetry pour ajouter ce depot git, ou télécharger une version
spécifique du package et installer un package local avec pip

S'assurer de passer comme variable d'environnement au moins une clé secrète soit dans
un fichier .env soit directement (au moment de la création de l'app
par gunicorn par exemple).

```
DJANGO_SECRET_KEY="random_secret_key_for_testing"
```

De manière optionnelle on peut également définir
```
DJANGO_BASE_DIR="root_directory_for_current_app"
```

## Utilisation

Au minimum, importer core.base_settings dans les settings principaux
et ajouter

```
AUTH_USER_MODEL = "users.User"
AGENDA_ICAL_FILE = chemin pour stocker le fichier ics des vacances
INSTALLED_APPS += [
    "dev",
    "core",
    "users",
    "agenda",
    "bulkimport",
    "utils",
    "quill_editor",
    "base_archives"
]
```

## Développement

Avant toute chose, créer un virtualenv et l'activer. Puis

```
poetry install --with dev
```

Le dossier ./tests contient des fichiers shell (linux) pour tester le code.
Avant de lancer `run` assurez-vous de :
 - renomer *.env_base* en *.env* et de remplir les champs
 - créer une base de donnée (du nom de NAME) PostgreSQL (pour tester le backup)

Une fois que la commande `run` s'exécute sans problème, il est possible
de tester plusieurs version de python et django via `tox`. Modifier
tox.ini au besoin.