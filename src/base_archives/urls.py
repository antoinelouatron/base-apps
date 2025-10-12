from django.urls import path
from base_archives import views

app_name = "archives"

urlpatterns = [
    path("download_db/", views.DownloadDb.as_view(), name="download_db"),
]
