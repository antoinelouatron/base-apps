#from allauth import app_settings as allauth_app_settings

#from allauth.account.forms import LoginForm

def set_prefs(request):
    if hasattr(request.user, "userpref"):
        ctx = request.user.userpref.to_context_data()
    else:
        ctx = {}
    if "darktheme" in request.COOKIES:
        dark = request.COOKIES["darktheme"] == "enabled"
        ctx["dark_theme"] = dark
    return ctx

# def auth_form(request):
#     """
#     add the custom authentication form.
#     """
#     if hasattr(request, "user") and request.user.is_authenticated:
#         return {}
#     return {
#         "auth_form": LoginForm(request=request),
#         #"SOCIAL_ACCOUNT_ENABLED": allauth_app_settings.SOCIALACCOUNT_ENABLED
#     }