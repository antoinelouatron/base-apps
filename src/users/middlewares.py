import users.models as um

class SeeAsMiddleware:
    """
    Voir le contenu comme un autre utilisateur.

    Aucune UI n'est livrée dans cette app.
    """
    def __init__(self, get_response):
        self.get_response = get_response
    
    def can_see_as(self, user: um.User):
        b = user.is_authenticated 
        b = b and (user.teacher or user.is_superuser or user.is_staff)
        return b

    # TODO : revoir la logique ?
    def __call__(self, request):
        if not request.user.is_authenticated:
            return self.get_response(request)
        see_as_user = request.GET.get("see_as", None)
        if see_as_user is None:
            see_as_user = request.session.get("see_as", None)
        if request.GET.get("reset_user"):
            request.session.pop("see_as", None)
        elif see_as_user and self.can_see_as(request.user):
            try:
                target_user = um.User.objects.filter(id=see_as_user).first()
            except (ValueError, TypeError):
                # id non numérique dans le paramètre GET
                target_user = None
            if target_user and target_user <= request.user:
                request.session["see_as"] = see_as_user
                request.user = target_user
            else:
                # cible inexistante ou non autorisée : on n'agit pas comme elle
                # et on purge la session pour ne pas persister un état invalide.
                request.user = um.AnonymousUser()
                request.session.pop("see_as", None)

        response = self.get_response(request)
        return response