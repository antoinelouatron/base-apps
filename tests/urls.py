"""
URLconf du harnais de test base_sites 2.0 (sans users/agenda, rapatriés chez le
consommateur). On ne câble que les modules génériques encore testés ici.
"""
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path, include

from rest_framework.authtoken.views import obtain_auth_token

urlpatterns = [
    path("admin/", admin.site.urls),
    path("login/", auth_views.LoginView.as_view(
        template_name="account/login.html",
        extra_context={"page_title": "Se connecter"},
    ), name="account_login"),
    path("logout/", auth_views.LogoutView.as_view(), name="account_logout"),
    path("api/get-token/", obtain_auth_token, name="api_obtain_token"),
    path("archives/", include(("base_archives.urls", "archives"))),
    path("import/", include("bulkimport.urls", namespace="import")),
]
