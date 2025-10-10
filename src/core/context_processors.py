"""
date: 2024-09-26
"""
def size(request):
    """
    Default screen min size to show nav/login as column and not overlay.
    """
    return {
        "min_size": "lg",
        "max_size": "xl",
    }