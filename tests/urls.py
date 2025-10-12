from core.base_urls import urlpatterns

# Add the archives app URLs
from django.urls import path, include

urlpatterns += [
    path("archives/", include(("base_archives.urls", "archives"))),
]
