import users.models as um
import users.permissions as up
from utils import menu
from utils.views import TemplateView, mixins

AGENDA_PERM : up.Permission = up.REF_TEACHER or up.SECRETARY or up.SCHOOL_ADMIN

def agenda_menus(user: um.User) -> menu.MenuList:
    ml = menu.MenuList()
    ml.add("Agenda", "agenda:index", "index")
    ml.add("Gestion des semaines", "agenda:weeks", "weeks")
    for level in um.Level.objects.all():
        # TODO : move that !
        ml.add(f"Colloscope {level.name}", "agenda:cscope_overview", f"cscope_overview_{level.id}", pk=level.id)
        if not AGENDA_PERM.has_permission(user, level=level):
            continue
        ml.add(f"Gestion EDT {level.name}","agenda:manage_periodic",  f"calendar_{level.id}", level_pk=level.id)
        ml.add(f"Événements ponctuels {level.name}", "agenda:manage_events", f"events_{level.id}", level_pk=level.id)
    

    return ml

class AgendaHome(mixins.UserIsStaffMixin, TemplateView):
    template_name = "agenda/home.html"
    SCRIPTS = ["home"]
    PAGE_TITLE = "Emploi du temps"

    def get_all_menus(self, ctx):
        base = agenda_menus(self.request.user)
        base.title = "Agenda"
        base.mark_current("index")
        account = self.account_menu_items()
        account.mark_current("agenda")
        return [account, base]
