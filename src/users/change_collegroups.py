"""
Created on Mon Nov 25 12:25:54 2019
"""
from django import forms
from django.db import transaction, models
from django.utils import timezone

import agenda.models as am
from agenda.models.attendance import AttComputer
import users.models as um


def get_form_class(number_list):

    values = [(None, "")] + [(n, n) for n in number_list]

    class GroupNumberChange(forms.ModelForm):

        class Meta:
            model = um.ColleGroup
            fields = ["nb"]
            widgets = {
                "nb": forms.Select(choices=values)
            }
            labels = {
                "nb": "Nouveau numéro"
            }

    return GroupNumberChange

class AttendanceFormset(forms.BaseModelFormSet):

    def __init__(self, base_numbers, *args, **kwargs):
        self.base_numbers = base_numbers
        super().__init__(*args, **kwargs)

    def clean(self):
        super().clean()
        numbers = set()
        if any(self.errors):
            return
        for form in self.forms:
            nb = form.cleaned_data["nb"]
            if nb in numbers:
                raise forms.ValidationError("Le numéro %i a été attribué au moins 2 fois" % nb)
            numbers.add(nb)
        if numbers != self.base_numbers:
            raise forms.ValidationError(
                "L'ensemble des numéros donnés ne correspond pas aux numéros de départ"
            )

    def save(self, commit=True):
        # no change in colle group objects
        # we only change linked StudentColleGroup's
        saved_forms = super().save(commit=False)
        # now instance have their new numbers ie we have to move
        # students from each to new ColleGroup
        return saved_forms

class ChangeAttendance():
    """
    Responsible for maintaining the attendance after a ColleGroup renumbering.

    We consider attendance-by-group remain the same, but students in each group can change.
    """

    def __init__(self):
        self.groups = um.ColleGroup.objects.order_by("nb")
        self.groups = self.groups.prefetch_related(
                "studentcollegroup_set__user"
        )
        self.group_list_nb = set(g.nb for g in self.groups)
        self.group_by_number = {g.nb: g for g in self.groups}

    def get_formset(self, **kwargs):
        """
        Prepare a formset, like get_form from ModelFormView.
        kwargs are keywords args to pass to constructed formset
        """
        form_class = get_form_class(self.group_list_nb)
        factory = forms.modelformset_factory(
            um.ColleGroup,
            form=form_class,
            fields=("nb",),
            extra=0,
            formset=AttendanceFormset
        )
        fset = factory(self.group_list_nb, queryset=self.groups, **kwargs)
        return fset

    def update_attendance(self, groups):
        """
        Make all attendance changes according to renumbering given by
        AttendanceFormset instance, which is cleaned
        """
        now = timezone.now()
        today = now.date()
        evs = list(am.PeriodicEvent.objects.all())
        evs += list(am.BaseEvent.objects.filter(begin__gte=now))
        evs += list(am.ToDo.objects.filter(date__gte=today))
        with transaction.atomic():
            # first, change StudentColleGroup association
            for g in groups:
                new_group = self.group_by_number[g.nb]
                for stg in g.studentcollegroup_set.all():
                    stg.group = new_group
                    stg.save()
            #update void status for all groups
            groups = um.ColleGroup.objects.annotate(
                c=models.Count("studentcollegroup")
            )
            groups.filter(c=0).update(void=True)
            groups.filter(void=True, c__gt=0).update(void=False)
            # then, update attendance strings
            AttComputer.changed_groups = True
            for ev in evs:
                ev.attendance_string = ev.attendance_string
        return True