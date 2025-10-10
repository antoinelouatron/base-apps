from .year import WeekManage, WeekNumberApi
from .api import (PersoTTView, WeekViewSet, TimelineView, NoteDetailView,
    CreateNoteView, CheckAgendaView)
from .events import (CreateUpdatePeriodic, ImportTimetable, ImportColleEvents,
    ImportCollePlanning, DeletePeriodicView, ExportTimetable, ImportDsEvents,
    StandaloneTimetable, ToDoManageView, ManageBaseEvent, DeleteBaseEventView,
    PrintTimetableView) 
from .home import AgendaHome, agenda_menus
from .inscriptions import (StudentInscriptionView, CancelInscriptionView,
    ManageInscriptionView, InscriptionListView, PastInscriptionsListView,
    DeleteInscriptionView)