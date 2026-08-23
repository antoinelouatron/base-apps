"""
Created on Fri Sep 25 07:43:57 2015
"""

import encodings
from io import TextIOWrapper

import django.forms
import django.forms.models as dfm
from django.core.exceptions import (
    ImproperlyConfigured, ValidationError, NON_FIELD_ERRORS,
)
from django.utils.translation import gettext as _, ngettext
import django.db.transaction

import bulkimport.forms.fields
import bulkimport.forms.widgets as widgets
import bulkimport.filetypes as ft
import bulkimport.dict_utils as du
from bulkimport.forms.report import ImportReport, RowError

# Metaclass to add form fields when class is created.

class FileImportFormMeta(dfm.ModelFormMetaclass):

    def __new__(mcs, name, bases, attrs):
        # get access to Meta class before creating ModelForm
        _meta = attrs.get('Meta', None)
        name_fields_names = getattr(_meta, 'name_fields', None)
        fields = getattr(_meta, 'fields', None)
        exclude = getattr(_meta, 'exclude', None)
        # auto-population af name mapping
        auto_populate = getattr(_meta, "auto_populate", False)
        # set exclude to name_fields_names if fields and exclude are missing
        if fields is None and exclude is None and _meta is not None:
            setattr(_meta, 'exclude', name_fields_names)
        new_class = super(FileImportFormMeta, mcs).__new__(mcs, name, bases, attrs)

        # Don't execute class customization for FileImportForm which does not declare
        # required Meta fields.
        if bases == (dfm.ModelForm,):
            return new_class
        # Following code is for classes which inherit from FileImportForm

        if _meta is None or not new_class._meta.model or name_fields_names is None:
            raise ImproperlyConfigured(
                "Creating a FileImportForm without the 'model' and 'name_fields' attributes "
                "is prohibited; form %s "
                "needs updating." % name
                )
        # add the 'magic' field
        name_attrs = getattr(_meta, "name_attrs", {})
        new_class.base_fields.update(
            _name_mapping=bulkimport.forms.fields.NameMappingField(
                name_fields_names,
                label=_("Correspondance de noms"),
                required=False,
                # for validation purpose
                auto_populate=auto_populate,
                add_attrs=name_attrs,
                help_text=_("Correspondance entre les nom de colonnes du fichier et les données attendues. Changer les valeurs pour refléter les données présentes dans le fichier."),  
                ),
            )
        new_class._name_fields = name_fields_names
        new_class._auto_populate = auto_populate
        # base form for validating read data : "atomic form"
        form_class = getattr(_meta, "form", None)
        if form_class is None:
            form_class = dfm.modelform_factory(new_class._meta.model, fields=name_fields_names)

        # dummy default post_save method for atomic forms
        def dummy_save(self, commit=False):
            pass
        setattr(form_class, "post_save", getattr(form_class, "post_save", dummy_save))
        new_class.atomic_form = form_class

        return new_class


def is_m2m(field_name, instance):
    try:
        field = instance._meta.get_field(field_name)
        return field.many_to_many
    except:
        return False

def with_metaclass(meta, *bases):
    # This requires a bit of explanation: the basic idea is to make a
    # dummy metaclass for one level of class instantiation that replaces
    # itself with the actual metaclass.  Because of internal type checks
    # we also need to make sure that we downgrade the custom metaclass
    # for one level to something closer to type (that's why __call__ and
    # __init__ comes back from type etc.).
    #
    # This has the advantage over six.with_metaclass in that it does not
    # introduce dummy classes into the final MRO.
    class metaclass(meta):
        __call__ = type.__call__
        __init__ = type.__init__
        def __new__(cls, name, this_bases, d):
            if this_bases is None:
                return type.__new__(cls, name, (), d)
            return meta(name, bases, d)
    return metaclass('temporary_class', None, {})


def quoted(names) -> str:
    return ", ".join("« %s »" % n for n in names)


def extension_error_message(e) -> str:
    """
    Message d'une extension refusée.

    Le cas fréquent est le classeur déposé tel quel : on explique comment
    l'exporter plutôt que de répondre « format non géré ».
    """
    accepted = _("Formats acceptés : %(list)s.") % {
        "list": ", ".join(e.supported or ft.supported_extensions())}
    if not e.extension:
        return _(
            "Le fichier « %(name)s » n'a pas d'extension. Renommez-le en "
            "« %(name)s.csv » (ou .json). %(accepted)s"
        ) % {"name": e.message, "accepted": accepted}
    if e.extension in ft.SPREADSHEET_EXTENSIONS:
        return _(
            "Le format %(ext)s n'est pas géré. Depuis votre tableur, utilisez "
            "Fichier > Enregistrer sous (ou Exporter) et choisissez « CSV », "
            "puis importez le fichier obtenu. %(accepted)s"
        ) % {"ext": e.extension, "accepted": accepted}
    return _("Le format %(ext)s n'est pas géré. %(accepted)s") % {
        "ext": e.extension, "accepted": accepted}


class FileImportForm(with_metaclass(FileImportFormMeta, dfm.ModelForm)):
    """
    Mandatory Meta attributes:
    name_fields: list of fields to retrieve from data file.
    model: base model class to create instance of.

    Optionnal Meta attribute:
    - fields: list of fields names, values will be shared between all created instances.
    - exclude: defaults to name_fields
    - form: a ModelForm subclass to validate/clean raw data. Used to create each instance.
    This class must have at least all fields listed in name_fields.
    It can define a post_save(self, commit=True) method (same argument as save).
    - name_attrs : dict field_name -> dict of attributes to add to the corresponding field in the form.
    - auto_populate : depecated, une cls.DEFAULT_NAME_MAPPING for more clarity.

    Optionnal class attribute:
    - DEFAULT_NAME_MAPPING: dict field_name -> default column name in data file.
    If defined, it must contain all fields listed in Meta.name_fields, and will
    
    - REQUIRED_COLUMNS: noms de champs dont la colonne doit exister dans le
    fichier. Par défaut, ceux dont le champ du formulaire atomique est
    obligatoire : une colonne facultative peut légitimement manquer.

    Each created atomic form instance will have a master_form attribute
    which is a reference to the FileImportForm instance.
    """
    add_css_classes = {
        "import_file": "m-2",
        "_encoding": "m-2",
        "_name_mapping": "*:flex *:flex-wrap *:justify-center"
    }

    # gabarit propre aux imports : il ajoute le rapport d'erreurs sous les
    # champs. Masque volontairement la property BaseForm.template_name.
    template_name = "bulkimport/forms/import_form.html"

    # au-delà, le détail des lignes fautives est remplacé par un décompte
    MAX_REPORTED_ROWS = 15
    # vérifier que les colonnes attendues existent avant de valider les lignes
    CHECK_COLUMNS = True
    REQUIRED_COLUMNS = None

    import_file = django.forms.FileField(
        label=_("Fichier à importer"),
        help_text=_("Json ou csv"),
        widget=django.forms.FileInput(attrs={
            "class": "p-2 rounded-sm border w-80",
            "placeholder": "Choisir un fichier"
        }),
    )
    _encoding = django.forms.ChoiceField(
        choices=[(k, v) for k, v in encodings.aliases.aliases.items()
                    if v in ["utf_8", "latin_1"]],
        widget=widgets.DataListInput(),
        initial="utf8",
        label=_("Encodage du fichier"),
        required=False)
    
    @classmethod
    def _get_initial_name_mapping(cls):
        """
        Correspondance de nom par défaut.
        Toutes les valeurs de Meta.name_fields doivent 
        être présentes dans DEFAULT_NAME_MAPPING pour que la correspondance
        soit proposée.
        """
        if not hasattr(cls, "DEFAULT_NAME_MAPPING"):
            return None
        for name in cls.Meta.name_fields:
            if name not in cls.DEFAULT_NAME_MAPPING:
                return None
        return {
            f"_name_mapping_{i}": cls.DEFAULT_NAME_MAPPING[name]
            for i, name in enumerate(cls.Meta.name_fields)
        }

    def __init__(self, *args, **kwargs):
        initial = kwargs.get("initial", {})
        nm = self._get_initial_name_mapping()
        if nm is not None:
            initial.update(_name_mapping=list(nm.values()))
        kwargs["initial"] = initial
        # le rapport existe dès la construction : le gabarit peut l'interroger
        # sans se demander si clean() est passé.
        self._report = ImportReport()
        self._forms = []
        super().__init__(*args, **kwargs)

    @property
    def import_report(self) -> ImportReport:
        return self._report

    def field_label(self, name) -> str:
        """
        Comment désigner une donnée dans un message d'erreur.

        Le nom de la colonne attendue passe avant tout : c'est ce que
        l'utilisateur a sous les yeux dans son fichier. Les noms de champs
        des modèles sont moins parlants.
        """
        if name in ("", NON_FIELD_ERRORS):
            return ""
        column = self._report.expected_columns.get(name)
        if column:
            return column
        attrs = getattr(self.Meta, "name_attrs", None) or {}
        label = attrs.get(name, {}).get("label")
        if label:
            return str(label)
        field = self.atomic_form.base_fields.get(name)
        if field is not None and field.label:
            return str(field.label)
        return name

    def _create_model_key_mapping(self, d, key_mapping):
        # key_mapping is the value of name_mapping field.
        # d is a dict obtained form the to-be-imported file
        # returns a drop-or-replace mapping including
        m = {k: None for k in d if k != du.EXTRA_VALUES_KEY}
        m.update(key_mapping)
        return m

    def clean__name_mapping(self):
        nm = self.cleaned_data['_name_mapping']
        if self._auto_populate:
            val = set(nm.values())
            for name in self._name_fields:
                if name not in val:
                    nm[name] = name
        return nm

    def _generate_dicts(self):
        # generator of the dictionnary to use for model creation
        # data are read directly from a file, no transformation is done
        # apart from the key translation
        nm = self.cleaned_data['_name_mapping']
        for d in self.cleaned_data['import_file']:
            km = self._create_model_key_mapping(d, nm)
            result = du.map_keys(d, km)
            if self.filter_dict(result):
                yield result

    @property
    def import_fields(self):
        return (self["_encoding"], self["_name_mapping"])

    @property
    def base_data(self):
        """
        Common data for all subforms
        """
        d = getattr(self, '_base_data', None)
        if d is None:
            d = self.cleaned_data.copy()
            del d['_name_mapping']
            del d['import_file']
            del d['_encoding']
            self._base_data = d
        return self._base_data

    ###################################################################
    # Contrôle des colonnes                                           #
    ###################################################################

    def get_required_name_fields(self) -> list[str]:
        """
        Champs dont l'absence de colonne condamne toutes les lignes.

        Par défaut, ceux dont le champ du formulaire atomique est obligatoire :
        une colonne facultative peut manquer sans que
        l'import n'ait de sens à échouer.
        """
        if self.REQUIRED_COLUMNS is not None:
            return list(self.REQUIRED_COLUMNS)
        required = []
        for name in self._name_fields:
            field = self.atomic_form.base_fields.get(name)
            if field is not None and field.required:
                required.append(name)
        return required

    def check_columns(self, file_keys, name_mapping):
        """
        Renseigne le rapport et retourne le message d'erreur, ou None.

        Une colonne mal nommée produisait jusqu'ici une erreur par ligne ;
        le diagnostic tient en une phrase, on le donne une fois.
        """
        report = self._report
        report.file_columns = list(file_keys)
        # name_mapping va de la colonne vers le champ ; la clé "" signale une
        # case de correspondance laissée vide.
        by_field = {}
        for column, field in name_mapping.items():
            if field is None:
                continue
            if column:
                by_field.setdefault(field, column)
        report.expected_columns = dict(by_field)
        known = set(file_keys)
        report.unused_columns = [
            c for c in file_keys if c not in name_mapping]

        if not self.CHECK_COLUMNS:
            # le rapport garde de quoi nommer les colonnes dans les messages
            # de ligne, mais aucune colonne n'est déclarée fautive.
            return None

        for name in self.get_required_name_fields():
            column = by_field.get(name)
            if column is None:
                report.unmapped_fields.append(self.field_label(name))
            elif column not in known:
                report.missing_columns.append(column)

        if not report.has_column_problem:
            return None

        parts = []
        if report.missing_columns:
            parts.append(ngettext(
                "Colonne introuvable dans le fichier : %(missing)s.",
                "Colonnes introuvables dans le fichier : %(missing)s.",
                len(report.missing_columns)
            ) % {"missing": quoted(report.missing_columns)})
        if report.unmapped_fields:
            parts.append(ngettext(
                "La correspondance de noms ne précise pas quelle colonne "
                "contient %(fields)s.",
                "La correspondance de noms ne précise pas quelles colonnes "
                "contiennent %(fields)s.",
                len(report.unmapped_fields)
            ) % {"fields": quoted(report.unmapped_fields)})
        if file_keys:
            parts.append(_("Le fichier contient : %(found)s.") % {
                "found": quoted(file_keys)})
        if len(file_keys) == 1:
            parts.append(_(
                "Une seule colonne a été détectée : le séparateur du fichier "
                "n'a probablement pas été reconnu. Les séparateurs acceptés "
                "sont la virgule, le point-virgule et la tabulation."))
        parts.append(_(
            "Corrigez les en-têtes du fichier, ou adaptez la correspondance "
            "de noms ci-dessus."))
        return " ".join(parts)

    ###################################################################
    # Lecture du fichier                                              #
    ###################################################################

    def _load_file(self, f, filename):
        """
        Convertit le fichier en DictIterable, ou lève une ValidationError
        qui dit quoi corriger.
        """
        try:
            return ft.load(f, filename)
        except ft.NotSupportedExtension as e:
            raise ValidationError(
                extension_error_message(e), code="bad_extension") from e
        except du.EmptyFile as e:
            raise ValidationError(
                _("Le fichier est vide."), code="empty_file") from e
        except du.NoHeader as e:
            raise ValidationError(
                _("La première ligne du fichier doit porter les noms des "
                  "colonnes. Elle ne contient aucun nom exploitable."),
                code="no_header") from e
        except du.BadFileContent as e:
            raise ValidationError(
                _("Le contenu du fichier est illisible : %(msg)s. Le fichier "
                  "est probablement tronqué ou mal formé."),
                code="bad_content", params={"msg": e.message}) from e
        except du.DifferentKeys as e:
            raise ValidationError(
                _("Les entrées du fichier n'ont pas toutes les mêmes "
                  "attributs : %(msg)s."),
                code="bad_format", params={"msg": e.args[0]}) from e
        except du.NotIterable as e:
            msg = _("Le fichier ne représente pas une liste de données.")
            if e.message:
                msg = _("Le fichier ne représente pas une liste de données : "
                        "%(msg)s.") % {"msg": e.message}
            raise ValidationError(msg, code="bad_format") from e

    def _encoding_error(self, encoding):
        return ValidationError(
            _("Le fichier n'a pas pu être lu avec l'encodage « %(enc)s » : il "
              "contient un caractère incompatible. Choisissez « latin_1 » dans "
              "le champ Encodage du fichier, ou réexportez le fichier en "
              "UTF-8."),
            code="bad_encoding", params={"enc": encoding})

    def clean(self):
        # we doesn't really have a model to clean here, so the warning in Django doc
        # concerning super().clean doesn't apply.

        # clean file text given encoding.
        uplf = self.cleaned_data.get('import_file', None)
        encoding = self.cleaned_data.get('_encoding', None)
        name_mapping = self.cleaned_data.get('_name_mapping', None)
        if uplf is None or encoding is None or name_mapping is None:
            return self.cleaned_data
        f = TextIOWrapper(uplf.file, encoding=encoding)
        try:
            # TextIOWrapper décode au fil de la lecture : un caractère
            # incompatible surgit soit au chargement, soit pendant la
            # validation des lignes.
            try:
                f_data = self._load_file(f, uplf.name)
                self._data_formatter = f_data.formatter
                self._file_data = f_data
                self.cleaned_data['import_file'] = f_data
                # renseigne aussi les libellés de colonnes utilisés par les
                # messages de ligne.
                msg = self.check_columns(f_data.keys, name_mapping)
                if msg is not None:
                    # inutile d'instancier le moindre sous-formulaire : toutes
                    # les lignes échoueraient pour la même raison.
                    raise ValidationError(msg, code="missing_columns")
                self._clean_subforms()
            except UnicodeDecodeError as e:
                raise self._encoding_error(encoding) from e
        finally:
            f.close()
        return self.cleaned_data

    ###################################################################
    # Validation ligne par ligne                                      #
    ###################################################################

    def _row_error(self, d, f_errors, extra=None) -> RowError:
        f_data = getattr(self, "_file_data", None)
        location = f_data.locate(d) if f_data is not None else ""
        nm = self.cleaned_data["_name_mapping"]
        # remettre les noms de colonnes du fichier pour que l'utilisateur
        # reconnaisse sa ligne
        reverse = {v: k for k, v in nm.items() if v is not None and k}
        data = du.map_keys(dict(d), reverse)
        errors = [(self.field_label(name), [e["message"] for e in messages])
                  for name, messages in f_errors.get_json_data().items()]
        if extra:
            errors.insert(0, ("", [_(
                "Cette ligne compte plus de valeurs que de colonnes. Une "
                "cellule contient probablement le séparateur « %(delim)s » "
                "sans être entre guillemets.") % {
                    "delim": getattr(f_data, "delimiter", None) or ","}]))
        return RowError(
            location=location,
            data=self._data_formatter(data),
            errors=errors,
        )

    def _summary_message(self, report) -> str:
        if report.total_rows and report.error_count >= report.total_rows:
            msg = ngettext(
                "La seule ligne du fichier comporte une erreur ; l'import est "
                "annulé en totalité.",
                "Aucune des %(total)d lignes du fichier n'a pu être importée ; "
                "l'import est annulé en totalité.",
                report.total_rows) % {"total": report.total_rows}
        else:
            msg = ngettext(
                "%(count)d ligne sur %(total)d comporte une erreur ; l'import "
                "est annulé en totalité.",
                "%(count)d lignes sur %(total)d comportent une erreur ; "
                "l'import est annulé en totalité.",
                report.error_count
            ) % {"count": report.error_count, "total": report.total_rows}
        if report.hidden_count:
            msg += " " + ngettext(
                "Le détail de la première est affiché sous le formulaire.",
                "Le détail des %(shown)d premières est affiché sous le "
                "formulaire.",
                len(report.rows)) % {"shown": len(report.rows)}
        else:
            msg += " " + _("Le détail est affiché sous le formulaire.")
        return msg

    def _clean_subforms(self):
        # create and validate all subforms
        # all errors in form/model validation will be reported as a file_import field error
        files = self.files.copy()
        del files['import_file']  # after that, files contains base data files
        forms = []
        report = self._report
        for d in self._generate_dicts():
            report.total_rows += 1
            # une ligne qui compte plus de valeurs que de colonnes est fausse,
            # même si les champs retenus se valident : la cellule fautive a
            # décalé toutes les suivantes.
            extra = d.pop(du.EXTRA_VALUES_KEY, None)
            # get_extra_form_kwargs est volontairement appelé à chaque ligne :
            # certains imports y fabriquent un objet neuf par ligne.
            form = self.atomic_form(d, files, **self.get_extra_form_kwargs())
            form.master_form = self
            inst = form.instance
            m2ms = []
            # copy base data in each created instance
            for k, v in self.base_data.items():
                if is_m2m(k, inst):  # instance is not saved, so it may not have pk
                    m2ms.append((k, v))
                else:
                    setattr(inst, k, v)
            if form.is_valid() and not extra:
                form._generated_data = d
                forms.append((form, m2ms))
            else:
                report.error_count += 1
                if len(report.rows) < self.MAX_REPORTED_ROWS:
                    report.rows.append(self._row_error(d, form.errors, extra))
        self._forms = forms
        report.hidden_count = report.error_count - len(report.rows)

        if report.error_count:
            self.add_error(
                "import_file",
                ValidationError(self._summary_message(report),
                                code="invalid_data"))
        elif report.total_rows == 0:
            # jusqu'ici un tel import était « réussi » et ne créait rien.
            self.add_error(
                "import_file",
                ValidationError(
                    _("Le fichier ne contient aucune ligne de données."),
                    code="no_data"))

    def filter_dict(self, d):
        """
        Override to filter some generated dict.
        No forms will be created for filtered-out dict.
        """
        return True

    def get_extra_form_kwargs(self):
        """
        Extra keyword arguments to be passed to atomic form creation.
        """
        return {}

    def save(self, commit=True):
        """
        Alias for save_all
        """
        return self.save_all(commit=commit)

    def save_all(self, commit=True):
        """
        Save all atomic forms (one for each entry in data file).
        Returns the list of all instances, saved to db if commit=True.

        Raise ValueError if an instance could not be created
        """
        if not self.is_valid():
            raise ValidationError("Cannot save a non valid form")
        forms = self._forms
        instances = []
        with django.db.transaction.atomic():
            for form, _m2ms in forms:
                inst = form.save(commit=commit)
                instances.append(inst)

            def save_m2m_field(f, values):
                for k, v in values:
                    f.instance._meta.get_field(k).save_form_data(f.instance, v)

            if not commit:
                def save_m2m():
                    for form, m2ms in forms:
                        form.save_m2m()
                        save_m2m_field(form, m2ms)
                        form.post_save(commit=True)
                self.save_m2m = save_m2m
            else:
                for form, m2ms in forms:
                    save_m2m_field(form, m2ms)
                    form.post_save(commit=commit)
        return instances
