from django.core.exceptions import PermissionDenied
import wrapt

@wrapt.decorator
def user_is_staff(wrapped, instance, args, kwargs):
    """
    To be used around dispatch method.

    When current user is not authenticated or is not part of the staff,
    return a 403/forbidden statuc code
    """
    request = args[0]
    if not request.user.is_active or not request.user.is_staff:
        raise PermissionDenied
    return wrapped(*args, **kwargs)

