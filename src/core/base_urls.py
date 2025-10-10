"""
URL configuration for sitelight project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.contrib import admin
from django.contrib.auth import views as auth_views
#from django.contrib.sitemaps import views as sitemaps_views
from django.http import HttpResponseRedirect
from django.urls import path, include

from rest_framework.authtoken.views import obtain_auth_token

#from . import sitemap
import users.forms as user_forms

# urlpatterns = []

# if settings.FLASHCARD_ACTIVE:
#     urlpatterns += [
#         path("flashcards/", include("flashcards.urls", namespace="flashcards")),
#     ]

# if settings.COLLES_ACTIVE:
#     urlpatterns += [
#         path("colles/", include("colles.urls", namespace="colles")),
#     ]

urlpatterns = [
    # path("sitemap.xml",
    #      #cache_page(86400)(sitemaps_views.sitemap), # cache for 1 day
    #      sitemaps_views.sitemap,
    #      {"sitemaps": {
    #         "pages": sitemap.PageSitemap,
    #         "chapters": sitemap.ChapterSitemap,
    #         "archives": sitemap.ArchiveSitemap,
    #         "blog": sitemap.BlogSitemap,
    #         "static": sitemap.StaticSitemap,
    #     }},
    #     name="django.contrib.sitemaps.views.sitemap"),
    path("admin/login/", lambda r: HttpResponseRedirect("/login/?next=/admin/")),
    path("admin/", admin.site.urls),
    path("login/", auth_views.LoginView.as_view(
        template_name="account/login.html",
        extra_context={"page_title": "Se connecter"},
        authentication_form=user_forms.AuthForm
    ), name="account_login"),
    #path("__not_an_url__", lambda a: None, name="account_signup"), # for reverse, not used
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
    #social login
    #path("login/google/", include("allauth.socialaccount.providers.google.urls")),
    #agenda app
    path("agenda/", include("agenda.urls", namespace="agenda")),
    path("profil/", include("users.urls", namespace="users")),
    path("import/", include("bulkimport.urls", namespace="import")),
    path("api/get-token/", obtain_auth_token, name="api_obtain_token"),
    # path("notes/", include("grades.urls", namespace="grades")),
    # path("archives/", include("archives.urls", namespace="archives")),
    # path("blog/", include("blog.urls", namespace="blog")),
    # path("flashcards/", include("flashcards.urls", namespace="flashcards")),
    # path("colles/", include("colles.urls", namespace="colles")),
    # path("", include("content.urls", namespace="content")),
]
