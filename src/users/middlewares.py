import users.models as um

class SeeAsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.user.is_authenticated:
            return self.get_response(request)
        see_as_user = request.GET.get("see_as", None)
        if see_as_user is None:
            see_as_user = request.session.get("see_as", None)
        if request.GET.get("reset_user"):
            request.session.pop("see_as", None)
        elif see_as_user and request.user.teacher:
            target_user = um.User.objects.filter(id=see_as_user).first()
            if target_user and target_user <= request.user:
                request.session["see_as"] = see_as_user
                request.user = target_user
            else:
                request.user = um.AnonymousUser()
                request.session["see_as"] = see_as_user

        response = self.get_response(request)
        return response