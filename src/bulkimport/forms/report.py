# -*- coding: utf-8 -*-
"""
Rapport d'un import de fichier.

Le formulaire d'import y dépose ce qu'il a constaté, le gabarit l'affiche.
Une seule source de vérité, pas de HTML fabriqué dans le code Python.
"""

import dataclasses


@dataclasses.dataclass(frozen=True)
class RowError:
    """
    Une ligne du fichier que la validation a refusée.
    """

    # « ligne 12 », « objet 3 », ou "" si la source ignore les positions
    location: str
    # la ligne telle qu'elle a été lue, rendue par le formatter du type de fichier
    data: str
    # (libellé de la colonne, messages) ; le libellé est vide pour une erreur
    # qui porte sur la ligne entière
    errors: list[tuple[str, list[str]]]


@dataclasses.dataclass
class ImportReport:
    """
    Ce qu'il faut dire à l'utilisateur quand un import échoue.
    """

    # colonnes lues dans le fichier
    file_columns: list[str] = dataclasses.field(default_factory=list)
    # nom de champ -> colonne attendue dans le fichier
    expected_columns: dict[str, str] = dataclasses.field(default_factory=dict)
    # colonnes obligatoires absentes du fichier
    missing_columns: list[str] = dataclasses.field(default_factory=list)
    # champs obligatoires dont la correspondance n'a pas été renseignée
    unmapped_fields: list[str] = dataclasses.field(default_factory=list)
    # colonnes présentes dans le fichier mais qui ne servent à rien : jamais
    # une faute, seulement une information
    unused_columns: list[str] = dataclasses.field(default_factory=list)

    total_rows: int = 0
    error_count: int = 0
    # tronquée à MAX_REPORTED_ROWS : un fichier entièrement faux ne doit pas
    # produire une page de mille messages
    rows: list[RowError] = dataclasses.field(default_factory=list)
    hidden_count: int = 0

    @property
    def has_errors(self) -> bool:
        return bool(self.missing_columns or self.unmapped_fields or self.rows)

    @property
    def has_column_problem(self) -> bool:
        return bool(self.missing_columns or self.unmapped_fields)
