"""
date: 2024-02-23
"""
import collections
import logging
from typing import Any

from django import forms, urls
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib import messages
from django.db import transaction
from django.http import QueryDict
from django.shortcuts import redirect
from django.views.generic.edit import UpdateView

from bulkimport import views as bv
from users import change_collegroups
import users.forms
import users.models as um
from utils import menu
from utils.views import TemplateView, ListView, View, FormView
from utils.views.mixins import JSONFormView, JSONResponseMixin, UserIsStaffMixin

class EditUserPref(LoginRequiredMixin, JSONFormView, UpdateView):
    
    form_class = users.forms.UserPrefForm
    template_attribute = "form_template_name"
    form_template_name = "users/user_pref_form.html"
    logger = logging.getLogger(__name__)
    raise_exception = True

    def get(self, *args, **kwargs):
        # no get here !
        return self.handle_no_permission()

    def get_object(self):
        # the difference between CreateView and UpdateView is only the value of
        # self.object, assigned to self.get_object() or None
        # We emulate this behaviour here.
        qs = um.UserPref.objects.filter(user=self.request.user)
        if len(qs) == 1:
            return qs[0] # edition mode
        # creation mode, explicit this.
        return None

    def serialize_object(self, obj):
        if len(self.form.changed_data) > 0:
            field_name = self.form.changed_data[0]
            # not used for now, but could be useful later
            if len(self.form.changed_data) != 1:
                self.logger.warning("Multiple change of preferences.")
            return {"fullName": um.UserPref._meta.get_field(field_name).verbose_name}
        self.logger.warning("No change of preference.")
        return {"fullName": "Préférence inconnue"}

    def form_valid(self, form):
        self.form = form
        form.instance.user = self.request.user
        return super().form_valid(form)

class SeeAsView(UserPassesTestMixin, ListView):
    template_name = "users/see_as.html"
    model = um.User
    raise_exception = True
    SCRIPTS = ["see_as"]
    PAGE_TITLE = "Espionnage"

    def test_func(self):
        b = self.request.user.is_authenticated
        return b and (self.request.user.teacher or self.request.user.is_staff)
    
    def get_queryset(self):
        filter = {}
        if not self.request.user.is_superuser:
            filter["is_staff"] = False
        return self.model.objects.filter(**filter).order_by(
            "student", "last_name", "first_name")
    
    def clean_get_params(self, referer):
        path_parts = referer.split("?")
        if len(path_parts) == 1:
            return referer
        GET = QueryDict(path_parts[1], mutable=True)
        if "see_as" in GET:
            GET.pop("see_as")
        if "reset_user" in GET:
            GET.pop("reset_user")
        params = GET.urlencode()
        if params:
            return f"{path_parts[0]}?{params}"
        return path_parts[0]
    
    def get_referer(self):
        ref = self.request.META.get("HTTP_REFERER", "/")
        # remove see_as and reset_user
        ref = self.clean_get_params(ref)
        if "?" in ref:
            ref += "&"
        else:
            ref += "?"
        return ref

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        ctx = super().get_context_data(**kwargs)
        ctx["referer"] = self.get_referer()
        return ctx

class AccountView(LoginRequiredMixin, FormView):
    """
    Account view
    """
    template_name = "users/account.html"
    login_url = "/login/"
    SCRIPTS = ["account"]
    PAGE_TITLE = "Mon compte"
    raise_exception = True
    form_class = PasswordChangeForm
        
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        instance, _ = um.UserPref.objects.get_or_create(user=self.request.user)
        context["pref_form"] = users.forms.UserPrefForm(instance=instance)
        if self.request.user.student:
            context["group"] = um.ColleGroup.objects.filter(studentcollegroup__user=self.request.user).first()
        subjects = um.Subject.objects.all()
        subjects = um.prepare_qs_for_component(subjects)
        levels = um.Level.objects.all()
        levels = um.prepare_qs_for_component(levels)
        context["user_roles"] = self.request.user.roles.display_data(
            subjects=subjects,
            levels=levels,
        )
        return context
    
    def get_all_menus(self, ctx):
        if self.request.user.teacher:
            account = self.account_menu_items()
            account.mark_current("account")
            return [account]
        return []
    
    def get_breadcrumb(self, ctx):
        bd = super().get_breadcrumb(ctx)
        mi = menu.MenuItem("Mon compte", url=urls.reverse("users:account"))
        bd.append(mi)
        return bd
    
    def popns(self, **kwargs):
        ns = super().popns(**kwargs)
        ns["urls"] = {
            "postPref": urls.reverse("users:edit_prefs"),
        }
        return ns
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs
    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.add_css_classes = {
            "old_password": "flex m-2 flex-wrap justify-center gap-2",
            "new_password1": "flex m-2 flex-wrap justify-center gap-2",
            "new_password2": "flex m-2 flex-wrap justify-center gap-2",
        }
        form.label_suffix = ""
        return form
    
    def form_valid(self, form):
        form.save()
        messages.success(self.request, "Mot de passe changé avec succès.")
        return redirect(urls.reverse("users:account"))

class UserListJson(LoginRequiredMixin, JSONResponseMixin, View):
    raise_exception = True

    def get(self, request, *args, **kwargs):
        return self.ok({})
    
    def get_data(self, ctx):
        qs = um.StudentColleGroup.objects.select_related("group", "user")
        qs.filter(user__is_active=True)
        users = collections.defaultdict(list)
        for scg in qs:
            users[scg.group.nb].append({
                "id": scg.user.id,
                "name": scg.user.get_full_name(),
            })
        return {"users": users}
    

class ImportUsersView(bv.ModelImportView):
    model_name = "users"
    title_name = "Utilisateurs"
    form_class = users.forms.ImportUsers

ImportUsersView.register("Utilisateurs")

class ListColleGroups(UserIsStaffMixin, ListView):
    template_name = "users/list_collegroups.html"
    SCRIPTS = ["home"]
    PAGE_TITLE = "Groupes de colles"

    def get_all_menus(self, ctx):
        account = self.account_menu_items()
        account.mark_current("collegroups")
        return [account]

    def get_breadcrumb(self, ctx=None):
        bd = super().get_breadcrumb(ctx)
        bd.append(menu.MenuItem(title="Groupes"))
        return bd

    def get_queryset(self):
        qs = um.ColleGroup.objects.order_by("nb")
        qs = qs.prefetch_related("studentcollegroup_set__user")
        return qs

class ChangeColleGroups(UserIsStaffMixin, FormView):

    template_name = "users/change_attendance.html"
    SCRIPTS = ["home"]
    PAGE_TITLE = "Renuméroter les groupes"

    def get_all_menus(self, ctx):
        account = self.account_menu_items()
        account.mark_current("collegroups")
        return [account]

    def get_breadcrumb(self, ctx=None):
        bd = super().get_breadcrumb(ctx)
        bd.append(menu.MenuItem(
            title="Groupes", url=urls.reverse("users:collegroups")
        ))
        bd.append(menu.MenuItem(title="Renuméroter"))
        return bd

    def get_form(self, form_class=None):
        kwargs = self.get_form_kwargs() # pass data if any
        return self.change_att.get_formset(**kwargs)

    def dispatch(self, request, *args, **kwargs):
        self.change_att = change_collegroups.ChangeAttendance()
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        try:
            with transaction.atomic():
                groups = form.save()
                self.change_att.update_attendance(groups)
                return redirect(urls.reverse("users:collegroups"))
        except:
            form._non_form_errors.append(forms.ValidationError("Erreur de sauvegarde."))
            return self.form_invalid(form)