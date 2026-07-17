import logging
from django import forms

from agenda.forms import events as afe
import agenda.models as am
from bulkimport.forms.importfile import FileImportForm
import users.models as um

class ColleEventAtomic(afe.PeriodicAtomic):

    subject = forms.CharField(required=False)
    last_name = forms.CharField(required=False, label="Nom du professeur")
    first_name = forms.CharField(required=False, label="Prénom du professeur")
    email = forms.EmailField(required=True, label="Email du professeur")
    teacher = forms.CharField(required=False)
    civilite = forms.CharField(required=False)
    classroom = forms.CharField(required=False)
    day = forms.CharField()
    #order = forms.IntegerField(required=False)

    logger = logging.getLogger(__name__)

    class Meta:
        model = am.ColleEvent
        fields = ["beghour", "endhour", "day",
        "subject", "teacher", "classroom", "abbrev", "subj"]

    def clean_day(self):
        val = self.cleaned_data["day"]
        if val in "0123456":
            return int(val)
        try:
            val = am.AbstractPeriodic.days_label.index(val.lower().strip())
            return val
        except ValueError:
            raise forms.ValidationError("Jour incorrect : %(val)s", params={"val": val},
                code="bad_day")
    
    def clean_email(self):
        val = self.cleaned_data["email"]
        if not val:
            raise forms.ValidationError("Email manquant", code="missing_email")
        return val.strip().lower()

    def clean(self):
        """
        SI aucun utilisateur avec l'email fourni n'est trouvé,
        on crée un nouvel utilisateur.

        Dans tous les cas on ajoute le rôle colleur correspondant à l'utilisateur
        référencé.
        """
        # Une Validation Error au niveau parent déclenche quand même
        # construct_instance, même si aucun teacher n'est encore là.
        self.cleaned_data["teacher"] = None
        cd = super().clean()

        if "email" not in cd or "subj" not in cd:
            raise forms.ValidationError("Données manquantes")

        teacher = um.User.objects.filter(email__iexact=cd["email"])
        subject = cd["subj"] # voir classe parent
        if teacher.count() == 1:
            self.logger.info('User found "%s"', cd["email"])
            teacher = teacher[0]
        elif teacher.count() > 1:
            self.logger.info('Multiple user "%s"', cd["email"])
            teacher = teacher[0]
        else:
            self.logger.info('Missing teacher "%s"', cd["email"])
            # create et pas create_colleur, vu qu'on ajoute le rôle colleur juste après
            teacher = um.User.objects.create(
                email=cd["email"],
                first_name=cd["first_name"],
                last_name=cd["last_name"],
                title=cd["civilite"],
            )
        cd["teacher"] = teacher
        teacher.roles.add(um.AtomicRole.create(
            colleur=True,
            subject=subject,
        ))
        teacher.save()
        return cd
    
    def save(self, commit=True):
        # pas besoin de calculer les participants
        obj = super().save(commit=False)
        if commit:
            obj.save()
        return obj


class ColleEventImport(afe.PeriodicImport):

    DEFAULT_NAME_MAPPING = {
        "beghour": "Début",
        "endhour": "Fin",
        "day": "Jour",
        "subject": "Matière",
        "last_name": "Nom",
        "first_name": "Prénom",
        "email": "Email",
        "civilite": "Civilité",
        "classroom": "Salle",
        "abbrev": "ID"
    }

    class Meta:
        model = am.ColleEvent
        fields = []
        name_fields = [
            "last_name", "first_name", "email","beghour", "endhour", "day",
            "subject", "civilite", "classroom", "abbrev"
        ]
        form = ColleEventAtomic
        auto_populate = True
        name_attrs = {
            "last_name": {"label": "Nom du professeur", "placeholder": "Nom"},
            "first_name": {"label": "Prénom du professeur", "placeholder": "Prénom"},
            "email": {"label": "Email du professeur", "placeholder": "Email"},
            "civilite": {"label": "Civilité du professeur", "placeholder": "Civilité"},
            "classroom": {"label": "Salle", "placeholder": "Salle"},
            "abbrev": {"label": "ID", "placeholder": "Numéro du créneau"}
        }

class CollePlanningAtomic(forms.ModelForm):

    week = forms.IntegerField()
    event = forms.CharField()
    group = forms.IntegerField()

    class Meta:
        model = am.CollePlanning
        fields = ["week", "event", "group"]

    def __init__(self, *args, weeks=None, events=None, groups=None, **kwargs):
        self.weeks = weeks
        self.events = events
        self.groups = groups
        super().__init__(*args, **kwargs)

    def _clean_field(self, obj_list, model_field_name, data_name, msg, param_name):
        val = self.cleaned_data[data_name]
        for obj in obj_list:
            if getattr(obj, model_field_name, None) == val:
                return obj
        raise forms.ValidationError(msg, params={param_name: val}, code="not_found")

    def clean_week(self):
        return self._clean_field(
            self.weeks,
            "nb",
            "week",
            "Semaine non trouvé %(nb)i",
            "nb"
        )

    def clean_event(self):
        return self._clean_field(
            self.events,
            "abbrev",
            "event",
            "Créneau non trouvé %(ev)s",
            "ev"
        )

    def clean_group(self):
        return self._clean_field(
            self.groups,
            "nb",
            "group",
            "Groupe non trouvé %(nb)i",
            "nb"
        )


class CollePlanningImport(FileImportForm):
    level = forms.ModelChoiceField(
        queryset=am.Level.objects,
        required=True,
        label="Classe",
        help_text="Classe à laquelle les événements seront associés"
    )

    class Meta:
        model = am.CollePlanning
        exclude = ["week", "event", "group", "postponed"]
        name_fields = ["week", "event", "group"]
        form = CollePlanningAtomic
        auto_populate = True

    def __init__(self, *args, level=None, **kwargs):
        super().__init__(*args, **kwargs)
        if level is not None:
            self.level = level
            self.fields["level"].widget = forms.HiddenInput()
            self.fields["level"].initial = self.level.pk
        
    
    def clean_level(self):
        if hasattr(self, "level"):
            return self.level
        self.level = self.cleaned_data.get("level")
        if self.level is None:
            raise forms.ValidationError("La classe doit être renseignée")
        return self.level

    def get_extra_form_kwargs(self):
        if not hasattr(self, "_weeks"):
            self._weeks = list(am.Week.objects.filter(active=True))
        weeks = self._weeks
        if not hasattr(self, "_events"):
            if hasattr(self, "level"):
                self._events = list(am.ColleEvent.objects.filter(subj__level=self.level))
            else:
                self._events = list()
        events = self._events
        if not hasattr(self, "_groups"):
            if hasattr(self, "level"):
                self._groups = list(um.ColleGroup.objects.filter(level=self.level))
            else:
                self._groups = list()
        groups = self._groups
        return {
            "weeks": weeks,
            "events": events,
            "groups": groups
        }
