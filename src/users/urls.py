"""
date: 2024-04-18
"""

from django.urls import path

import users.views as uv

app_name = "users"
# prefixed with /profil/
urlpatterns = [
    path("", uv.AccountView.as_view(), name="account"),
    path("preferences/",uv.EditUserPref.as_view() ,name="edit_prefs"),
    path("espion/", uv.SeeAsView.as_view(), name="see_as"),
    path("list/", uv.UserListJson.as_view(), name="list"),
    path("groupes-de-colle/", uv.ListColleGroups.as_view(), name="collegroups"),
    path("groupes-de-colle/changer/", uv.ChangeColleGroups.as_view(), name="change_collegroups"),
]
