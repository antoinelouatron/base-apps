from .year import WeekManage, WeekNumberApi
from .api import (PersoTTView, WeekViewSet, TimelineView, NoteDetailView,
    CreateNoteView, CheckAgendaView)
from .events import (CreateUpdatePeriodic, ImportTimetable, ImportColleEvents,
    ImportCollePlanning, DeletePeriodicView, ExportTimetable, ImportDsEvents,
    StandaloneTimetable, ToDoManageView, ManageBaseEvent, DeleteBaseEventView,
    PrintTimetableView) 
from .home import AgendaHome, agenda_menus
# from inscriptions.views import (StudentInscriptionView, CancelInscriptionView,
#     ManageInscriptionView, InscriptionListView, PastInscriptionsListView,
#     DeleteInscriptionView)
from .cscope import (ConsultCscopeView, PersoCscopeView, CscopeOverview)