"""
Created on Fri Sep 25 07:43:57 2015
"""

import encodings
from io import TextIOWrapper

import django.forms
import django.forms.models as dfm
from django.utils import safestring
from django.core.exceptions import (
    ImproperlyConfigured, ValidationError,
)
from django.utils.translation import gettext as _
import django.db.transaction
from django.template.defaultfilters import pluralize

import bulkimport.forms.fields
import bulkimport.forms.widgets as widgets
import bulkimport.filetypes as ft
import bulkimport.dict_utils as du

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
    It can define a post_save(self, commit=True) method (same argument as save),
    and a pre_clean(self).

    Each created atomic form instance will have a master_form attribute
    which is a reference to the FileImportForm instance.
    """
    add_css_classes = {
        "import_file": "m-2",
        "_encoding": "m-2",
        "_name_mapping": "*:flex *:flex-wrap *:justify-center"
    }

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

    def _create_model_key_mapping(self, d, key_mapping):
        # key_mapping is the value of name_mapping field.
        # d is a dict obtained form the to-be-imported file
        # returns a drop-or-replace mapping including
        m = {k: None for k in d}
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

    def _clean_subforms(self):
        # create and validate all subforms
        # all errors in form/model validation will be reported as a file_import field error
        files = self.files.copy()
        del files['import_file']  # after that, files contains base data files
        forms = []
        errors = []
        for d in self._generate_dicts():
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
            if form.is_valid():
                form._generated_data = d
                forms.append((form, m2ms))
            else:
                errors.append((d, form.errors))
        if len(errors) > 0:
            for d, f_errors in errors:
                nm = self.cleaned_data["_name_mapping"]
                # reverse key mapping for error display
                nm = {v: k for k, v in nm.items() if v is not None}
                data = du.map_keys(d, nm)
                self.add_error(
                    "import_file",
                    ValidationError(
                        safestring.mark_safe(
                            _("La donnée %(data)s a produit %(err_text)s : %(errors)s") % {
                                "data": self._data_formatter(data),
                                "errors": f_errors.as_ul(),
                                "err_text": pluralize(len(f_errors), "l'erreur,les erreurs")
                            }),
                        code="invalid_data",
                    )
                )
        self._forms = forms

    def clean(self):
        # we doesn't really have a model to clean here, so the warning in Django doc
        # concerning super().clean doesn't apply.

        # clean file text given encoding.
        uplf = self.cleaned_data.get('import_file', None)
        encoding = self.cleaned_data.get('_encoding', None)
        if uplf is None or encoding is None:
            return self.cleaned_data
        f = TextIOWrapper(uplf.file, encoding=encoding)
        try:
            f_data = ft.load(f, uplf.name)
        except ft.NotSupportedExtension as e:
            raise ValidationError(
                _(f'Extension de fichier non reconnue : {e.message}'),
                code="bad_extension"
            ) from e
        except ft.NotIterable as e:
            raise ValidationError(
                _('Le fichier ne représente pas une liste de données.'),
                code="bad_format"
            ) from e
        except du.DifferentKeys as e:
            raise ValidationError(
                _('Les attributs des objets sont différents : %(msg)s'),
                code="bad_format",
                params={'msg': e.args[0]}
            ) from e
        self._data_formatter = f_data.formatter
        self.cleaned_data['import_file'] = f_data
        self._clean_subforms()
        f.close()
        return self.cleaned_data

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
            for form, _ in forms:
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
