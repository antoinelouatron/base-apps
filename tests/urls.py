"""
URLconf du harnais de test base_sites.

Reprend le câblage qui vivait dans core.base_urls (supprimé : chaque consommateur
possède désormais son URLconf). Tant que users/agenda vivent encore dans base_sites,
on les câble ici pour la suite de tests.
"""
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.http import HttpResponseRedirect
from django.urls import path, include

from rest_framework.authtoken.views import obtain_auth_token

import users.forms as user_forms

urlpatterns = [
    path("admin/login/", lambda r: HttpResponseRedirect("/login/?next=/admin/")),
    path("admin/", admin.site.urls),
    path("login/", auth_views.LoginView.as_view(
        template_name="account/login.html",
        extra_context={"page_title": "Se connecter"},
        authentication_form=user_forms.AuthForm
    ), name="account_login"),
    path("logout/", auth_views.LogoutView.as_view(), name="account_logout"),
    path("reset-mdp/", auth_views.PasswordResetView.as_view(
        template_name="account/password_reset.html",
        email_template_name="users/password/reset_email.html",
    ),
         name="account_reset_password"),
    path("reset-mdp/par-cle/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="account/password_reset_from_key.html",
            extra_context={"page_title": "Créer un nouveau mot de passe"},
            form_class=user_forms.SetPasswordForm
        ),
        name="password_reset_confirm"),
    path("reset-mdp/confirmation/", auth_views.PasswordResetDoneView.as_view(
        template_name="account/password_reset_done.html"),
        name="password_reset_done"),
    path("reset-mdp/succes/", auth_views.PasswordResetCompleteView.as_view(
        template_name="account/password_reset_from_key_done.html"),
         name="password_reset_complete"),
    path("agenda/", include("agenda.urls", namespace="agenda")),
    path("profil/", include("users.urls", namespace="users")),
    path("api/get-token/", obtain_auth_token, name="api_obtain_token"),
    # apps testées spécifiquement par le harnais
    path("archives/", include(("base_archives.urls", "archives"))),
    path("import/", include("bulkimport.urls", namespace="import")),
]