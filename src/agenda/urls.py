from django.urls import path, include
from rest_framework.routers import DefaultRouter
import agenda.views as av

router = DefaultRouter()
router.register("week", av.WeekViewSet, basename="week_api")

inscriptions = (
    [
        path("<int:pk>/", av.StudentInscriptionView.as_view(), name="add"),
        path("supprimer/<int:pk>/", av.CancelInscriptionView.as_view(),
             name="cancel"),
        path("gerer/", av.ManageInscriptionView.as_view(), name="manage"),
        path("gerer/<int:pk>/", av.ManageInscriptionView.as_view(), name="manage"),
        path("", av.InscriptionListView.as_view(), name="list"),
        path("api/list/", av.PastInscriptionsListView.as_view(), name="list_passed"),
        path("supprimer-seance/<int:pk>/", av.DeleteInscriptionView.as_view(), name="delete"),
    ],
    "inscription"
)

api_urls = router.urls + [
    # TODO : move api call here
]

app_name = "agenda"
urlpatterns = [
    path("", av.AgendaHome.as_view(), name="index"),
    path("semaines/", av.WeekManage.as_view(), name="weeks"),
    path("semaine/valider/", av.WeekNumberApi.as_view(), name="weeks_update"),
    path("edt/<int:week>/", av.PersoTTView.as_view(), name="user_timetable"),
    path("edt/<int:week>/<int:user_id>/", av.PersoTTView.as_view(), name="user_timetable"),
    path("edt/creation/", av.CreateUpdatePeriodic.as_view(), name="manage_periodic"),
    path("edt/creation/<int:level_id>/", av.CreateUpdatePeriodic.as_view(),
        name="manage_periodic"),
    path("edt/check/<int:level_id>/", av.CheckAgendaView.as_view(), name="check_agenda"),
    path("edt/imprimer/<int:level_id>/", av.PrintTimetableView.as_view(),
        name="print_timetable"),
    path("edt/creation/supprimer/", av.DeletePeriodicView.as_view(), name="delete_periodic"),
    path("edt/creation/uniques/", av.ManageBaseEvent.as_view(), name="manage_events"),
    path("edt/creation/uniques/<int:pk>/", av.ManageBaseEvent.as_view(), name="manage_events"),
    path("edt/creation/uniques/supprimer/<int:pk>/", av.DeleteBaseEventView.as_view(), name="delete_event"),
    path("edt/export/<int:level_id>/", av.ExportTimetable.as_view(), name="export_timetable"),
    path("edt/personnel/", av.StandaloneTimetable.as_view(), name="personal_timetable"),
    path("timeline/", av.TimelineView.as_view(), name="timeline"),
    path("memo/creation/", av.CreateNoteView.as_view(), name="note_create"),
    path("memo/<int:event>/<int:week>/", av.NoteDetailView.as_view(),
         name="note_detail"),
    path("todo/", av.ToDoManageView.as_view(), name="todo"),
    path("todo/<int:pk>/", av.ToDoManageView.as_view(), name="todo"),
    path("api/", include((api_urls, "api"))),
    path("inscriptions/", include(inscriptions)),
]