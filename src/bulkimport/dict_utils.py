"""
Created on Sat Sep 26 19:23:33 2015
"""

# Clé sentinelle donnée à csv.DictReader pour récupérer les valeurs d'une ligne
# qui compte plus de champs que l'en-tête. Sans elle, ces valeurs sont perdues
# en silence et l'utilisateur ne comprend pas pourquoi sa ligne est fausse.
EXTRA_VALUES_KEY = "__valeurs_en_trop__"

# Au-delà, une valeur est tronquée dans les messages d'erreur : une cellule qui
# contient un paragraphe entier ne doit pas noyer le reste de la ligne.
MAX_VALUE_LENGTH = 40


def map_keys(d, key_mapping):
    """
    Change keys in d.

    key_mapping must be a dictionnary of hashable -> replacement
    Each key in d found as a key in key_mapping is replaced by the value in key_mapping.

    If replacement is None, d[key] will be deleted.

    No check for key duplication is made.
    """
    for old_key in key_mapping:
        if old_key in d:
            if key_mapping[old_key] is None:
                del d[old_key]
            else:
                d[key_mapping[old_key]] = d.pop(old_key)
    return d


class Row(dict):
    """
    Une ligne lue dans un fichier, enrichie de sa position d'origine.

    C'est un dict, et rien d'autre : map_keys peut la muter en place, un
    formulaire peut la recevoir comme `data`, et tout code qui ignore
    `line_no` continue de fonctionner. Le numéro est un attribut de classe
    pour qu'une Row construite sans position, ou copiée par dict.copy(),
    reste utilisable.
    """

    line_no = None

    def __init__(self, mapping=None, /, line_no=None, **kwargs):
        super().__init__(mapping or {}, **kwargs)
        if line_no is not None:
            self.line_no = line_no


def line_of(d):
    """
    Position d'origine d'une ligne, ou None si la source ne la connait pas.
    """
    return getattr(d, "line_no", None)


def format_row(d) -> str:
    """
    Représentation lisible d'une ligne, pour un message d'erreur.

    Les colonnes vides sont passées sous silence : elles n'aident pas à
    reconnaitre la ligne dans le fichier d'origine.
    """
    parts = []
    for k, v in d.items():
        if k == EXTRA_VALUES_KEY:
            continue
        if v is None or v == "":
            continue
        text = str(v)
        if len(text) > MAX_VALUE_LENGTH:
            text = text[:MAX_VALUE_LENGTH] + "..."
        parts.append("%s=%s" % (k, text))
    if not parts:
        return "(ligne vide)"
    return ", ".join(parts)


class DictIterable():
    """
    Simple wrapper around an iterable of dict.
    The use case is when all dict have same keys, and the first parameter is an iterable of
    these keys.

    optionnal parameter formatter is a function taking a dict and returning a string representing
    this dict (useful to represent dict extracted from file)

    position_label nomme ce qu'est une entrée pour ce type de fichier : une
    « ligne » dans un csv, un « objet » dans un json qui n'a pas de lignes.
    """

    def __init__(self, keys, dict_iterable, formatter=format_row,
                 position_label="ligne", delimiter=None):
        self.keys = list(keys)
        self._data = dict_iterable
        self.formatter = formatter
        self.position_label = position_label
        self.delimiter = delimiter

    def __iter__(self):
        return self._data.__iter__()

    def locate(self, d) -> str:
        """
        « ligne 12 », « objet 3 », ou "" si la position est inconnue.
        """
        no = line_of(d)
        if no is None:
            return ""
        return "%s %s" % (self.position_label, no)


class ImportFileError(Exception):
    """
    Le fichier n'a pas pu être lu, ou n'a pas la structure attendue.

    Classe de base : le formulaire d'import n'a ainsi qu'une branche de
    secours à écrire pour tous les échecs de lecture.
    """

    def __init__(self, message=""):
        self.message = message
        super().__init__(message)


class NotIterable(ImportFileError):
    """
    Le fichier est lisible mais ne représente pas une liste de données.
    """


class BadFileContent(ImportFileError):
    """
    Le contenu est syntaxiquement cassé (json tronqué, csv malformé).
    """


class EmptyFile(ImportFileError):
    """
    Le fichier ne contient rien.
    """


class NoHeader(ImportFileError):
    """
    Le fichier n'a pas de ligne d'en-tête exploitable.
    """


class DifferentKeys(ImportFileError, KeyError):
    """
    Les entrées du fichier n'ont pas toutes les mêmes attributs.

    Hérite encore de KeyError : du code appelant peut l'attraper sous cette
    forme.
    """


def is_injection(d, E, F):
    """
    Check if dictionary d is an injection from sequences E to F.

    E must be the keys and F the values of d.
    >>> d = {'a': 1, 'b': 2}
    >>> is_injection(d, 'ab', (1,1))
    False
    >>> is_injection(d, 'ab', (1,3))
    False
    >>> is_injection(d, 'ac', (1,3))
    False
    >>> is_injection(d, 'ac', (1,2))
    False
    >>> is_injection(d, 'ab', (1,2))
    True
    >>> is_injection(d, 'ab', (1,2,3))
    True
    """
    n = len(d)
    if len(E) != n:
        return False
    occurrences = {}
    for f in F:
        occurrences[f] = False  # has this element been encountered yet
    for e in E:
        if e not in d:
            return False
        oc = occurrences.get(d[e], True)  # if d[e] is not an element of F, oc == True
        if oc:
            return False
        occurrences[d[e]] = True
    return True

def is_bijection(d, E, F):
    """
    Check if dictionary d is a bijection between sequences E and F.

    E must be the keys ans F the values of d.
    >>> d = {'a': 1, 'b': 2}
    >>> is_bijection(d, 'ab', (1,1))
    False
    >>> is_bijection(d, 'ab', (1,3))
    False
    >>> is_bijection(d, 'ac', (1,3))
    False
    >>> is_bijection(d, 'ac', (1,2))
    False
    >>> is_bijection(d, 'ab', (1,2))
    True
    """
    n = len(d)
    if len(E) != n or len(F) != n:
        return False
    return is_injection(d, E, F)
