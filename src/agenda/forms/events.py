"""
date: 2024-04-10
"""
import datetime
from django import forms

from bulkimport.forms.importfile import FileImportForm
import agenda.models as am
import users.models as um
from utils.forms import widgets, filter_qs

class BaseAttendanceForm(filter_qs.FilterQuerySetForm):

    _attendance_string = forms.CharField(label="Participants", required=False)

    def clean__attendance_string(self):
        """
        Clean the attendance string. It should be a comma-separated list of
        integers or ranges of integers.
        """
        att_str = self.cleaned_data["_attendance_string"]
        # compute attendance once, hacking the descriptor
        am.AttendanceEvent.attendance_string.att_computer(att_str.split(","))
        # can raise ValidationError if the string is not valid
        return att_str

    def save(self, commit=True):
        inst = super().save(commit=commit)
        # see ModelForm.save_instance : we have to postpone the saving of manytomany
        # relations.
        def save_m2m():
            inst.attendance_string = self.cleaned_data["_attendance_string"] or ""
            inst.save() # save new string
        if commit:
            save_m2m()
        else:
            self.save_m2m = save_m2m
        return inst

class PeriodicForm(BaseAttendanceForm):

    add_css_classes = {
        "beghour": "p-1 w-1/2",
        "endhour": "p-1 w-1/2",
        "begweek": "p-1 w-1/2",
        "endweek": "p-1 w-1/2",
        "label": "m-1",
        "subj": "m-1",
        "day": "m-1",
        "periodicity": "m-1",
        "classroom": "m-1",
        "_attendance_string": "flex w-full justify-center m-1 flex-wrap",
    }

    class Meta:
        model = am.PeriodicEvent
        fields = ["begweek", "endweek", "beghour", "endhour", "label", "subj",
                  "day", "periodicity", "classroom"]
        widgets = {
            "label": forms.TextInput(
                attrs={"placeholder": "Nom à afficher", "title": "Nom à afficher",
                "class": "w-full"}),
            "begweek": forms.TextInput(
                attrs={"placeholder": "1ère semaine", "title": "1ère semaine",
                "class": "w-full"}),
            "endweek": forms.TextInput(
                attrs={"placeholder": "Dernière semaine", "title": "Dernière semaine",
                "class": "w-full"}),
            "beghour": forms.TextInput(
                attrs={"placeholder": "Heure début", "title": "Heure début",
                "class": "w-full"}),
            "endhour": forms.TextInput(
                attrs={"placeholder": "Heure fin", "title": "Heure fin",
                "class": "w-full"}),
            "periodicity": forms.TextInput(attrs={"class": "w-16"}),
            "classroom": forms.TextInput(attrs={"class": "w-16"}),
        }
        labels = {
            "beghour": "",
            "endhour": "",
            "begweek": "",
            "endweek": "",
            "day": "Jour ",
            "periodicity": "Période",
            "label": "",
        }

class PeriodicAtomic(BaseAttendanceForm):
    """
    ModelForm for PeriodicEvent which takes short attendance list. The accepted format is
    [<att>(,<att>,...)] where att is either a colle group nb or a teacher display_name.
    """

    beghour = forms.TimeField(input_formats=["%H:%M:%S", "%H:%M", "%H"])
    endhour = forms.TimeField(input_formats=["%H:%M:%S", "%H:%M", "%H"])
    subj = forms.IntegerField(required=False)

    class Meta:
        model = am.PeriodicEvent
        fields = ["begweek", "endweek", "beghour", "endhour", "label", "subject",
            "day", "periodicity", "classroom", "subj"]
    
    def clean(self):
        cdata = super().clean()
        # find subj from subject
        subject_label = cdata.get("subject")
        if subject_label is None or not hasattr(self.master_form, "subjects"):
            self.add_error("subject", f"Impossible de trouver la matière {subject_label}")
            return cdata
        subject = self.master_form.subjects.get(subject_label.lower())
        if subject:
            cdata["subj"] = subject
        else:
            raise forms.ValidationError(f"Matière inconnue : {subject_label}")
        return cdata

class PeriodicImport(FileImportForm):
    level = forms.ModelChoiceField(
        queryset=am.Level.objects,
        required=True,
        label="Classe",
        help_text="Classe à laquelle les événements seront associés"
    )

    class Meta:
        form = PeriodicAtomic
        model = am.PeriodicEvent
        fields = []
        name_fields = ["begweek", "endweek", "beghour", "endhour", "label", "subject",
            "day", "periodicity", "classroom", "_attendance_string"]
        auto_populate = True
    
    def _get_subject_dict(self, level: um.Level) -> dict[str, int]:
        """
        Return a dictionary mapping subject short names to Subject instances
        for the given level.
        """
        return {subj.name.lower(): subj for subj in am.Subject.objects.filter(level=level)}
    
    def clean_level(self):
        self.level = self.cleaned_data.get("level")
        if self.level is None:
            raise forms.ValidationError("La classe doit être renseignée")
        self.subjects = self._get_subject_dict(self.level)
        return self.level

class BaseEventForm(BaseAttendanceForm):

    add_css_classes = {
        "begin": "flex justify-between m-1",
        "end": "flex justify-between m-1",
        "label": "flex justify-center m-1",
        "classroom": "flex justify-center m-1",
        "_attendance_string": "flex flex-col w-full justify-center items-center my-1 flex-wrap",
    }

    class Meta:
        model = am.BaseEvent
        fields = ["begin", "end", "label", "classroom", "override"]
        widgets = {
            "label": forms.TextInput(
                attrs={"placeholder": "Nom à afficher", "title": "Nom à afficher"}),
            "classroom": forms.TextInput(
                attrs={"placeholder": "Salle (facultatif)", "title": "Salle"}),
            "begin": widgets.DateTimePicker(),
            "end": widgets.DateTimePicker(),
            "override": forms.HiddenInput(),
        }
        labels = {
            "label": "",
            "classroom": "",
        }

LABEL_DATALIST = (
    "Math 1",
    "Math 2",
    "TP info",
    "IMT",
)
# TODO : améliorer l'interface utilisateur !
class InscriptionForm(forms.ModelForm):

    add_css_classes = {
        "teacher": "w-full flex justify-center m-1",
        "begin": "m-1",
        "end": "m-1",
        "max_students": "m-1",
        "label": "m-1",
        "classroom": "w-full flex justify-center m-1",
    }

    class Meta:
        model = am.InscriptionEvent
        fields = ["teacher", "label", "max_students", "begin", "end", "classroom",
            "attendants"]
        labels = {
            "max_students": "Nombre de places",
            "label": "Nom à afficher",
        }
        widgets = {
            "begin": widgets.DateTimePicker(),
            "end": widgets.DateTimePicker(),
            "max_students": forms.NumberInput(
                attrs={"placeholder": "Nombre de place", "title": "Nombre de place"},
            ),
            "label": widgets.DataListText(
                attrs={"placeholder": "Nom à afficher",
                    "title": "Nom à afficher"},
                datalist=LABEL_DATALIST,
            ),
            "classroom": forms.TextInput(
                attrs={"placeholder": "Salle (facultatif)", "title": "Salle"},
            ),
        }
        labels = {
            "teacher": "Professeur",
            "begin": "Début",
            "end": "Fin",
            "label": "",
            "classroom": "",
            "max_students": "",
        }
    
    def __init__(self, *args, teacher=None, **kwargs):
        if teacher is None:
            raise ValueError("teacher must be set")
        self.teacher = teacher
        if teacher.is_staff and "instance" in kwargs and kwargs["instance"] is not None:
            # remove initial value for teacher
            kwargs["initial"] = {}
        super().__init__(*args, **kwargs)
        if not teacher.is_staff:
            self.fields["teacher"].widget = forms.HiddenInput()
        self.fields["teacher"].queryset = um.User.objects.filter(
            is_active=True, teacher=True)
        self.fields["attendants"].queryset = um.User.objects.filter(
            teacher=False, is_active=True).order_by("last_name", "first_name")
    
    def clean_teacher(self):
        if not self.teacher.is_staff:
            return self.teacher
        return self.cleaned_data["teacher"]

class DsAtomic(BaseAttendanceForm): # not a good name !
    date = forms.DateField()
    begin = forms.TimeField()
    end = forms.TimeField()
    classroom = forms.CharField(required=False)

    class Meta:
        model = am.BaseEvent
        fields = ("begin", "end", "label")

    def clean(self):
        # cdata = super().clean()
        cdata = self.cleaned_data

        begin = cdata.get("begin")

        end = cdata.get("end")
        date = cdata.get("date")

        if date is None or begin is None or end is None:
            return cdata
        # make sure to set begin and end before we can raise a ValidationError
        # If we can't change those, model will try to validate wrong data and
        # throw "TypeError: expected string or bytes-like object"
        # when trying to convert begin which is now a time object
        cdata["begin"] = am.ensure_aware(datetime.datetime.combine(date, begin))
        cdata["end"] = am.ensure_aware(datetime.datetime.combine(date, end))
        return cdata

class DsImport(FileImportForm):

    class Meta:
        form = DsAtomic
        model = am.BaseEvent
        fields = []
        name_fields = ("begin", "end", "date", "label", "_attendance_string", "classroom")
        auto_populate = True

class NoteForm(forms.ModelForm):

    add_css_classes = {
        "comment": "flex flex-col w-full m-1 text-center",
    }

    class Meta:
        model = am.Note
        fields = ("target_week", "target_event", "comment")
        labels = {
            "comment": "Contenu de la note"
        }
        widgets = {
            "target_week": forms.HiddenInput(),
            "target_event": forms.HiddenInput()
        }


class ToDoForm(BaseAttendanceForm):

    add_css_classes = {
        "date": "m-1",
        "label": "m-1",
        "long_label": "w-full m-1 flex flex-col",
        "students": "m-1",
        "all": "m-1",
    }
    
    students = forms.BooleanField(label="Élèves", required=False)
    all = forms.BooleanField(label="Tous", required=False)

    class Meta:
        model = am.ToDo
        fields = ("date", "label", "long_label", "msg_level")
        widgets = {
            "date": widgets.DatePicker(),
            "label": forms.TextInput(
                attrs={"placeholder": "Nom de la tâche", "title": "Nom de la tâche"}),
            "long_label": forms.Textarea(
                attrs={"placeholder": "Description", "title": "Description"}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["_attendance_string"].required = False
    
    def save(self, commit=True):
        inst = super().save(commit=False)
        # boolean fields takes precedence over attendance_string
        studs = self.cleaned_data.get("students")
        all = self.cleaned_data.get("all")
        if not studs and not all:
            if commit:
                inst.save()
                self.save_m2m()
        else:
            filter = {} # all takes precedence over students
            if studs and not all:
                filter["student"] = True
            def save_m2m():
                inst.save()
                inst.attendants.set(um.User.objects.filter(**filter))
            if commit:
                save_m2m()
            else:
                self.save_m2m = save_m2m
        return inst