from utils import menu
from utils.views import TemplateView, mixins

def agenda_menus():
    ml = menu.MenuList()
    ml.add("Agenda", "agenda:index", "index")
    ml.add("Gestion des semaines", "agenda:weeks", "weeks")
    ml.add("Gestion EDT","agenda:manage_periodic",  "calendar")
    ml.add("Événements ponctuels", "agenda:manage_events", "events")
    return ml

class AgendaHome(mixins.UserIsStaffMixin, TemplateView):
    template_name = "agenda/home.html"
    SCRIPTS = ["home"]
    PAGE_TITLE = "Emploi du temps"

    def get_all_menus(self, ctx):
        base = agenda_menus()
        base.title = "Agenda"
        base.mark_current("index")
        account = self.account_menu_items()
        account.mark_current("agenda")
        return [account, base]
