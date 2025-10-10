from django.urls import reverse

def without_trailing_pk(namespaces_name, pk_name="pk", **kwargs):
    kwargs[pk_name] = 0
    complete_url = reverse(namespaces_name, kwargs=kwargs)
    return complete_url[:-2]

def without_trailing(namespaces_name: str, **names: dict[str, str]):
    """
    construct an url with given kwargs, but remove all trailing parts.
    """
    complete_url = reverse(namespaces_name, kwargs=names)
    for v in names.values():
        complete_url = complete_url[:-len(v)-1]
    return complete_url