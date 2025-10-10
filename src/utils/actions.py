from django import urls

from .components import Component

class SeeAs(Component):
    template_name = "users/components/see_as.html"

class UnSeeAs(Component):
    template_name = "users/components/unsee_as.html"

class LinkAction(Component):
    """
    Abstract component for link buttons 
    """
    url_name = ""

    @property
    def target(self) -> str:
        return urls.reverse(self.url_name, kwargs=self.get_url_kwargs())
    
    def get_url_kwargs(self) -> dict:
        return {}

# class AvatarValidation(LinkAction):
#     template_name = "users/components/avatar_validation.html"
#     url_name = "admin:users_avatar_changelist"

#     def __init__(self, avatar_validation=0):
#         self.avatar_validation = avatar_validation

class AdminLink(LinkAction):
    template_name = "users/components/admin_link.html"
    url_name = "admin:index"
    label = "Admin"

# class AddInscription(LinkAction):
#     template_name = "content/components/add_action.html"
#     url_name = "agenda:inscription:manage"
#     label = "Inscriptions"

# class ToDo(LinkAction):
#     template_name = "content/components/add_action.html"
#     url_name = "agenda:todo"
#     label = "Rappels"
