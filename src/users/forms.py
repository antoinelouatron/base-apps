from django import forms
import django.contrib.auth.forms as auth_forms

from bulkimport.forms.importfile import FileImportForm
from users import models as um
import utils.forms.widgets as pw

class AuthForm(auth_forms.AuthenticationForm):

    remember = forms.BooleanField(required=False, label="Se souvenir de moi")

    def clean_remember(self):
        remember = self.cleaned_data.get("remember", False)
        if remember:
            self.request.session.set_expiry(60 * 60 * 24 * 30)  # 30 days
        else:
            self.request.session.set_expiry(0)  # Browser close
        return remember

class SetPasswordForm(auth_forms.SetPasswordForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["new_password1"].widget.attrs.update({
            "class": "text-lg pl-2",
            "minlength": 8,
        })
        self.fields["new_password2"].widget.attrs.update({
            "class": "text-lg pl-2",
            "minlength": 8,
        })

class UserPrefForm(forms.ModelForm):

    class Meta:
        exclude = ("user", )
        model = um.UserPref
        field_classes = {
            "dark_theme": pw.SliderField
        }
        widgets = {
            "dark_theme": pw.SliderCheckbox(attrs={
                "data-prop": "dark_theme",
                "class": "ajax-pref"
            })
        }

class UserAtomicForm(forms.ModelForm):

    colle_group = forms.IntegerField(required=False)

    class Meta:
        model = um.User
        fields = ["title", "first_name", "last_name", "email"]

    def clean(self):
        cd = super().clean()
        self.colle_group = cd.get("colle_group", None)
        if self.colle_group is not None:
            self.colle_group, _ = um.ColleGroup.objects.get_or_create(nb=self.colle_group, void=False)
        return cd

    def post_save(self, commit=True):
        inst = self.instance

        def save_group():
            if self.colle_group is not None:
                um.StudentColleGroup.objects.get_or_create(
                    user=inst,
                    group=self.colle_group
                )
        if not commit:
            old_save_m2m = self.save_m2m

            def save_m2m():
                old_save_m2m()
                save_group()
            self.save_m2m = save_m2m
        else:
            save_group()
        return inst

class ImportUsers(FileImportForm):

    teacher = forms.BooleanField(required=False, label="Professeur")
    student = forms.BooleanField(required=False, label="Élève")

    class Meta:
        model = um.User
        fields = ["teacher", "student"]
        form = UserAtomicForm
        auto_populate = True
        name_fields = ["first_name", "last_name", "title", "email", "colle_group"]


class UserForm(forms.ModelForm):
    """
    Form for displaying a user with their roles.
    """

    class Meta:
        model = um.User
        fields = ["title", "first_name", "last_name", "email", "is_active"]

class UserRoleForm(forms.Form):
    id = forms.IntegerField(widget=forms.HiddenInput())
    role = forms.ChoiceField(choices=[])
    level = forms.ChoiceField(choices=[], required=False, label="Classe")
    subject = forms.ChoiceField(choices=[], required=False, label="Matière")

    def __init__(self, *args, superuser=False, **kwargs):
        super().__init__(*args, **kwargs)
        choices = [
            ("", "--------"),
            (um.AtomicRole.STUDENT, "Élève"),
            (um.AtomicRole.TEACHER, "Enseignant"),
            (um.AtomicRole.COLLEUR, "Colleur"),
            (um.AtomicRole.REF_TEACHER, "Prof référent")
        ]
        # TODO : make school_admin able to add secretary/admin roles
        if superuser:
            choices += [
                (um.AtomicRole.SECRETARY, "Secrétaire"),
                (um.AtomicRole.SCHOOL_ADMIN, "Administrateur")
            ]
        self.fields["role"].choices = choices
        self.fields["level"].choices = [(level.pk, level) for level in um.Level.objects.all()]
        self.fields["subject"].choices = [(subject.pk, subject) for subject in um.Subject.objects.all()]

    def save(self):
        data = self.cleaned_data
        role = um.AtomicRole(
            role=data["role"],
            level=data.get("level"),
            subject=data.get("subject")
        )
        return role