"""
date: 2024-04-18
"""

from django.urls import path, include

import users.views as uv

app_name = "users"
# prefixed with /profil/

api = [
    path("gerer-utilisateurs/modifier/<int:pk>/", uv.ManageUserView.as_view(),
        name="manage_user"),
]

urlpatterns = [
    path("", uv.AccountView.as_view(), name="account"),
    path("preferences/",uv.EditUserPref.as_view() ,name="edit_prefs"),
    path("espion/", uv.SeeAsView.as_view(), name="see_as"),
    path("list/", uv.UserListJson.as_view(), name="list"),
    path("gerer-utilisateurs/", uv.UserListsView.as_view(), name="manage_users"),
    path("gerer-utilisateurs/ajouter-role/", uv.AddRoleView.as_view(), name="add_role"),
    path("gerer-utilisateurs/enlever-role/", uv.RemoveRoleView.as_view(),
        name="remove_role"),
    path("groupes-de-colle/", uv.ListColleGroups.as_view(), name="collegroups"),
    path("groupes-de-colle/changer/", uv.ChangeColleGroups.as_view(),
        name="change_collegroups"),
    path("api/", include((api, "api"))),
]
