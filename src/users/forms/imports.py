"""
date: 2025-07-23

Les utilisateurs sont identifiés par leurs emails, noms, prénoms
"""

from django import forms

import bulkimport.forms.importfile as bf
import users.models as um

CHOICES_CSS_CLASSES = "p-2 border rounded-sm"

class UserAtomicForm(forms.ModelForm):
    """
    Utilisé comme formclass pour tous les formulaires d'import qui suivent.
    """
    master_form: bf.FileImportForm

    colle_group = forms.IntegerField(required=False)

    class Meta:
        model = um.User
        fields = ["first_name", "last_name", "email"]

    def __init__(self, *args, role: um.AtomicRole = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.role = role    
    
    def find_existing(self) -> um.User | None:
        """
        Return the user already in DB matching this row (by email, the unique
        key), or None. Email is matched case-insensitively since User.save()
        lowercases it and the unique constraint is on Lower("email").
        """
        email = self.cleaned_data.get("email")
        if not email:
            return None
        return um.User.objects.filter(email__iexact=email).first()

    def _post_clean(self):
        # Cross-import idempotence: if the user already exists in DB, bind it
        # *before* model validation so the unique-email constraint sees an
        # update (its pk is excluded) rather than a duplicate. Otherwise
        # validation fails before save() can reuse the instance, since all
        # sub-forms are validated before any is saved.
        existing = self.find_existing()
        if existing is not None:
            self.instance = existing
        super()._post_clean()

    def save(self, commit=True) -> um.User:
        # Within-batch merge: a sibling row with the same email may have been
        # saved earlier in this very import (the DB was still empty at
        # validation time, so _post_clean could not see it). Re-bind here so
        # duplicate rows collapse into one user, e.g. a student listed under
        # two levels ends up with both student roles.
        existing = self.find_existing()
        if existing is not None:
            self.instance = existing
        instance = super().save(commit=False)
        if self.role:
            instance.roles.add(self.role)
        if commit:
            instance.save()
        return instance
    
    def post_save(self, commit=True) -> um.User:
        """
        Méthode ajoutée/appelée par FileImportForm.
        """
        cg = self.cleaned_data.get("colle_group", None)
        def save_group():
            if cg is not None and self.role.level:
                groups = self.master_form.colle_groups.setdefault(
                    self.role.level, {})
                level_inst = self.master_form.levels.get(
                    int(self.role.level),
                    um.Level.objects.get(pk=self.role.level)
                )
                if cg not in groups:
                    group, _ = um.ColleGroup.objects.get_or_create(
                        level=level_inst, nb=cg)
                    groups[cg] = group
                # on a unicité user-collegroup dans StudentColleGroup
                # d'où le get_or_create par sécurité/ en cas d'import multiple
                um.StudentColleGroup.objects.get_or_create(
                    user=self.instance, group=groups[cg])
        if not commit:
            old_save_m2m = self.save_m2m

            def save_m2m():
                old_save_m2m()
                save_group()
            self.save_m2m = save_m2m
        else:
            save_group()
        return self.instance
        

class TeacherAtomicForm(UserAtomicForm):
    """
    Form to import teachers.
    """
    class Meta(UserAtomicForm.Meta):
        fields = UserAtomicForm.Meta.fields + ["title"]


def add_level(cls: type):
    """
    Add a field to a UserAtomicForm class.

    The field is added to the Meta.fields of the class and values
    must refer to the name attribute of an existing instance of um.Level.
    
    Cache the instance lookup in master_form to avoid multiple queries.
    """

    class AtomicForm(cls):
        """
        Atomic form to import a single instance of model_class.
        """
        level = forms.CharField(required=True)
        
        def clean(self):
            cd = super().clean()
            level_name = cd.get("level")
            if level_name:
                try:
                    level = level_name.lower()
                    level_inst = self.master_form.levels.get(
                        level,
                        um.Level.objects.get(name__iexact=level_name)
                    )
                    self.master_form.levels[level] = level_inst
                    self.role.level = level_inst.pk
                except um.Level.DoesNotExist:
                    raise forms.ValidationError(
                        f"La classe '{level_name}' n'existe pas.")
            return cd
    
    return AtomicForm

def add_subject(cls: type):
    """
    Add a field to a UserAtomicForm class.

    The field is added to the Meta.fields of the class and values
    must refer to the name attribute of an existing instance of um.Subject.
    
    Cache the instance lookup in master_form to avoid multiple queries.
    """

    class AtomicForm(cls):
        """
        Atomic form to import a single instance of model_class.
        """
        subject = forms.CharField(required=False)
        
        def clean(self):
            cd = super().clean()
            if self.role.level is None:
                raise forms.ValidationError(
                    "La classe doit être renseignée avec la matière.")
            subject_name = cd.get("subject")
            if subject_name:
                try:
                    subject = subject_name.lower()
                    subject_dict = self.master_form.subjects.get(
                        self.role.level,
                        {}
                    )
                    if subject in subject_dict:
                        subject_inst = subject_dict[subject]
                    else:
                        subject_dict[subject] = um.Subject.objects.get(
                            name__iexact=subject_name, level=self.role.level)
                        subject_inst = subject_dict[subject]
                    self.master_form.subjects[self.role.level] = subject_dict
                    self.role.subject = subject_inst.pk
                except um.Subject.DoesNotExist:
                    raise forms.ValidationError(
                        f"La matière '{subject_name}' n'existe pas.")
            return cd
    
    return AtomicForm

class BaseImportForm(bf.FileImportForm):
    """
    Classe de base pour tous les formulaires spécifiques suivants.
    """
    DEFAULT_NAME_MAPPING = {
        "first_name": "Prénom",
        "last_name": "Nom",
        "email": "Email",
        "title": "Civilité",
        "level": "Classe",
        "subject": "Matière",
        "colle_group": "Groupe"
    }

    class Meta: # dummy Meta, inherit and override in child classes
        model = um.User
        name_fields = []
        fields = []
        name_attrs = {
            "first_name": {"label": "Prénom", "placeholder": "Prénom"},
            "last_name": {"label": "Nom", "placeholder": "Nom"},
            "email": {"label": "Email", "placeholder": "Email"},
            "title": {"label": "Civilité", "placeholder": "Civilité"},
            "level": {"label": "Classe", "placeholder": "Classe"},
            "subject": {"label": "Matière", "placeholder": "Matière"},
            "colle_group": {"label": "Groupe", "placeholder": "N° du groupe de colle"}
        }
    
    # @classmethod
    # def _get_initial_name_mapping(cls):
    #     """
    #     Correspondance de nom par défaut.
    #     """
    #     # beware of KeyError
    #     return {
    #         f"_name_mapping_{i}": cls.DEFAULT_NAME_MAPPING[name]
    #         for i, name in enumerate(cls.Meta.name_fields)
    #     }

    def __init__(self, *args, **kwargs):
        # le code commenté a été bougé dans la classe parent.

        # initial = kwargs.get("initial", {})
        # nm = self._get_initial_name_mapping()
        # initial.update(_name_mapping=list(nm.values()))
        # kwargs["initial"] = initial
        kwargs["label_suffix"] = " "
        super().__init__(*args, **kwargs)
        self.levels = {} # level_name.lower() -> Level instance
        self.subjects = {} # level_pk -> {subject_name.lower(): Subject instance}
        self.colle_groups = {} # level_pk -> {group_number: ColleGroup}

class ForLevelImportForm(BaseImportForm):
    """
    Formulaire de base pour l'import ciblé sur une classe donnée.

    La classe doit être donnée par la vue
    """

    level = forms.ModelChoiceField(
        queryset=um.Level.objects.none(),
        required=True,
        widget=forms.HiddenInput()  # level will be set in the view
    )

    class Meta(BaseImportForm.Meta):
        pass

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["level"].queryset = um.Level.objects.all()

class StudentImportForm(ForLevelImportForm):
    """
    Importer un fichier csv contenant une liste d'élèves pour une
    classe donnée (fixée par la vue).
    """

    class Meta(BaseImportForm.Meta):
        model = um.User
        name_fields = ["first_name", "last_name", "email", "colle_group"]
        form = UserAtomicForm
        fields = []

    def get_extra_form_kwargs(self):
        """
        Passé à chaque sous-formulaire construit.
        """
        if not self.is_valid():
            return {}
        return {
            "role": um.AtomicRole(
                um.AtomicRole.STUDENT,
                level=self.cleaned_data["level"].pk)
        }

class StudentWithLevelImportForm(BaseImportForm):
    """
    Cette fois la classe est spécifiée dans le fichier importé.
    """
    
    class Meta(StudentImportForm.Meta):
        form = add_level(UserAtomicForm)
        name_fields = StudentImportForm.Meta.name_fields + ["level"]

    def get_extra_form_kwargs(self):
        return {
            # level will be set in the form, use dummy value for creation
            "role": um.AtomicRole(um.AtomicRole.STUDENT, level=0)
        }

class TeacherImportForm(BaseImportForm):
    """
    Importer des enseignants.
    Matière choisie dans le formulaire, pas dans le fichier.
    """
    level = forms.ModelChoiceField(
        queryset=um.Level.objects.none(),
        required=True,
        label="Classe",
        widget=forms.Select(attrs={"class": CHOICES_CSS_CLASSES})
    )
    subject = forms.ModelChoiceField(
        queryset=um.Subject.objects.none(),
        required=True,
        label="Matière",
        widget=forms.Select(attrs={"class": CHOICES_CSS_CLASSES})
    )

    class Meta(BaseImportForm.Meta):
        model = um.User
        name_fields = ["first_name", "last_name", "email", "title"]
        form = TeacherAtomicForm
        fields = []
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["level"].queryset = um.Level.objects.all()
        self.fields["subject"].queryset = um.Subject.objects.all()

    def get_extra_form_kwargs(self):
        """
        Return extra kwargs to pass to the form.
        """
        if not self.is_valid():
            return {}
        return {
            "role": um.AtomicRole(
                um.AtomicRole.TEACHER,
                level=self.cleaned_data["level"].pk,
                subject=self.cleaned_data["subject"].pk
            )
        }

class TeacherWithSubjectImportForm(BaseImportForm):
    """
    Cette fois la matière est spécifiée dans le fichier importé.
    """

    class Meta(TeacherImportForm.Meta):
        form = add_subject(add_level(TeacherAtomicForm))
        name_fields = ["first_name", "last_name", "email", "title", "level", "subject"]

    def get_extra_form_kwargs(self):
        """
        Return extra kwargs to pass to the form.
        """
        return {
            "role": um.AtomicRole(
                um.AtomicRole.TEACHER,
                level=0,
                subject=0
            )
        }

class TeacherForLevelImportForm(ForLevelImportForm):
    """
    Importer des enseignants pour une classe donnée.
    Matière choisie dans le formulaire, pas dans le fichier.
    """

    class Meta(TeacherImportForm.Meta):
        form = add_subject(TeacherAtomicForm)
        name_fields = TeacherImportForm.Meta.name_fields + ["subject"]

    def get_extra_form_kwargs(self):
        """
        Return extra kwargs to pass to the form.
        """
        if not self.is_valid():
            return {"role": um.AtomicRole(
                um.AtomicRole.TEACHER,
                level=None,
                subject=0
            )}
        return {
            "role": um.AtomicRole(
                um.AtomicRole.TEACHER,
                level=self.cleaned_data["level"].pk,
                subject=0
            )
        }

class ColleurImportForm(TeacherImportForm):
    """
    Importer des colleurs.
    Matière choisie dans le formulaire, pas dans le fichier.
    """

    class Meta(TeacherImportForm.Meta):
        pass

    def get_extra_form_kwargs(self):
        """
        Return extra kwargs to pass to the form.
        """
        kwargs = super().get_extra_form_kwargs()
        if "role" in kwargs:
            kwargs["role"].role = um.AtomicRole.COLLEUR
        return kwargs

class ColleurForLevelImportForm(TeacherForLevelImportForm):
    """
    Importer des colleurs pour une classe donnée.
    Matière choisie dans le formulaire, pas dans le fichier.
    """

    class Meta(TeacherForLevelImportForm.Meta):
        pass

    def get_extra_form_kwargs(self):
        kwargs = super().get_extra_form_kwargs()
        if "role" in kwargs:
            kwargs["role"].role = um.AtomicRole.COLLEUR
        return kwargs

class ColleurWithSubjectImportForm(TeacherWithSubjectImportForm):
    """
    Import form for colleurs with their subject given in the file.
    """

    class Meta(TeacherWithSubjectImportForm.Meta):
        pass

    def get_extra_form_kwargs(self):
        return {
            "role": um.AtomicRole(
                um.AtomicRole.COLLEUR,
                level=0,
                subject=0
            )
        }