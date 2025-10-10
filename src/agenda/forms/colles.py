import logging
from django import forms

import agenda.models as am
from bulkimport.forms.importfile import FileImportForm
import users.models as um

class ColleEventAtomic(forms.ModelForm):

    beghour = forms.TimeField(input_formats=["%H:%M:%S", "%H:%M", "%H"])
    endhour = forms.TimeField(input_formats=["%H:%M:%S", "%H:%M", "%H"])
    subject = forms.CharField(required=False)
    teacher = forms.CharField(required=False)
    civilite = forms.CharField(required=False)
    classroom = forms.CharField(required=False)
    day = forms.CharField()
    order = forms.IntegerField(required=False)

    logger = logging.getLogger(__name__)

    class Meta:
        model = am.ColleEvent
        fields = ["beghour", "endhour", "day",
        "subject", "teacher", "classroom", "order", "abbrev"]

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

    def clean(self):
        """
        Defaults to a random subject and teacher
        """
        cd = self.cleaned_data
        teacher = um.User.objects.filter(
            title=cd.get("civilite", ""), last_name=cd.get("teacher", ""),
            teacher=True)
        if teacher.count() == 1:
            teacher = teacher[0]
        elif teacher.count() > 1:
            self.logger.info('Multiple user "%s" "%s"', cd["civilite"], cd["teacher"])
            teacher = um.User.objects.filter(teacher=True)[0]
        else:
            self.logger.info('Missing teacher "%s" "%s"', cd["civilite"], cd["teacher"])
            teacher = um.User.objects.create_teacher(last_name=cd["teacher"],
                title=cd["civilite"],first_name="")
        cd["teacher"] = teacher
        return cd


class ColleEventImport(FileImportForm):

    class Meta:
        model = am.ColleEvent
        fields = []
        name_fields = [
            "beghour", "endhour", "day", "subject",
            "teacher", "civilite", "classroom", "order", "abbrev"
        ]
        form = ColleEventAtomic
        auto_populate = True

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

    class Meta:
        model = am.CollePlanning
        name_fields = ["week", "event", "group"]
        form = CollePlanningAtomic
        auto_populate = True

    def get_extra_form_kwargs(self):
        if not hasattr(self, "_weeks"):
            self._weeks = list(am.Week.objects.filter(active=True))
        weeks = self._weeks
        if not hasattr(self, "_events"):
            self._events = list(am.ColleEvent.objects.all())
        events = self._events
        if not hasattr(self, "_groups"):
            self._groups = list(um.ColleGroup.objects.all())
        groups = self._groups
        return {
            "weeks": weeks,
            "events": events,
            "groups": groups
        }
