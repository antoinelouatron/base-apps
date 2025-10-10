"""
Created on Fri Nov 27 15:41:17 2015
"""
import abc
import logging

from django.conf import settings
from django.contrib.auth.mixins import UserPassesTestMixin
from django.http import JsonResponse
from django.views.generic import TemplateView, View
import django.template as template

from . import static_assets, json_utils, rich_results
from utils import menu, actions

class UserIsStaffMixin(UserPassesTestMixin):
    raise_exception = True

    def test_func(self) -> bool:
        return self.request.user.is_staff

class UserIsTeacherMixin(UserPassesTestMixin):
    """
    Test en plus avec le modèle User utilisé ici.
    """
    raise_exception = True

    def test_func(self) -> bool:
        b = self.request.user.is_authenticated and self.request.user.teacher
        b = b or self.request.user.is_staff
        return b

class JSONResponseMixin():
    """
    A mixin that can be used to render a JSON response.
    Default to calling self.ok with the result of self.get_data

    The Json response will have "status" set to ok or error.
    """

    def get_data(self, context, **kwargs) -> dict:
        """
        Returns an object that will be serialized as JSON by json.dumps().
        """
        return context
    
    def ok(self, context, **response_kwargs) -> JsonResponse:
        """
        context is passed as such to get_data
        """
        return JsonResponse(
            json_utils.json_data(self.get_data(context)), safe=False,
            **response_kwargs
        )

    def error(self, msg, error_data={} , **response_kwargs) -> JsonResponse:
        """
        Use kwargs to pass additionnal data to json response
        """
        return JsonResponse(
            json_utils.error_data(msg, add_data=error_data), safe=False,
            **response_kwargs
        )
    
    def render_to_response(self, context, **response_kwargs):
        return self.ok(context, **response_kwargs)

class BaseJsonView(JSONResponseMixin, View):
    """
    Base view for JSON response.
    """

    def get(self, request, *args, **kwargs):
        return self.render_to_response({})

class RenderableMixin():
    """
    Début de la gestion des templates pour les vues basées sur JSON.
    """
    html_context_name = "html"
    template_attribute = "template_name"

    def get_data(self, context, **kwargs):
        tpl = template.loader.get_template(getattr(self, self.template_attribute))
        html = tpl.render(context)
        kwargs[self.html_context_name] = html
        return kwargs


class JSONTemplateView(RenderableMixin, JSONResponseMixin, TemplateView):
    """
    Simple wrapper around JSONResponseMixin.
    Generates html with self.template_name and context data.
    get_data returns {'html': html} in addition to provided kwargs as data serialized to JSON

    default context passed to get_data is the context returned
    by get_context_data.
    """


class JSONFormMixin(RenderableMixin, abc.ABC):
    """
    Similar to JSONTemplateView.
    Only accessible by post, create an object via a modelform.
    If the form is invalid, send a json response with error status and
    html corresponding to faulty form.
    If the form is valid, send a json response with ok status and
    a serialization of saved instance.

    form_template_name must refer to a template rendering only the target form,
    passed as template parameter "form".
    """
    template_attribute = "form_template_name"

    @abc.abstractmethod
    def serialize_object(self, obj) -> dict:
        """
        Serialize created object to send back via AJAX
        """
        return {}

    def final_data(self, serialization: dict) -> dict:
        """
        Return the final data to send back.
        serialization is the result of serializing form.save()
        """
        return serialization

    def form_valid(self, form):
        """
        Serialize and send OK code
        """
        inst = form.save()
        data = json_utils.json_data(self.final_data(self.serialize_object(inst)))
        return JsonResponse(data, safe=False)
    
    def render_form(self, form):
        return self.get_data({"form": form})

    def form_invalid(self, form):
        """
        Return json data to re-render the form, with errors.
        """
        data = json_utils.error_data("Invalid Form")
        data.update(self.render_form(form))
        data["form_errors"] = str(form.errors)
        return JsonResponse(data, safe=False)

class JSONFormView(JSONFormMixin, JSONResponseMixin):
    """
    Base view for full form management in AJAX. Add a class based view
    after in MRO.
    """
    # do not change Inheritance order, we need get_data from Form mixin


class ActionsMixin():

    @property
    def user(self):
        return self.request.user

    def get_actions(self, ctx):
        act = []
        if self.user.is_superuser:
            #act.append(actions.AvatarValidation(self.user.get_pending_avatars()))
            act.append(actions.AdminLink())
        if self.user.is_authenticated and (self.user.teacher or self.user.is_staff):
            act.append(actions.SeeAs())
            #act.append(actions.AddInscription())
        elif self.request.session.get("see_as", None):
            act.append(actions.UnSeeAs())
        # if self.user.is_staff:
        #     act.append(actions.ToDo())
        return act

class MenuMixin(ActionsMixin):
    """
    Responsible for menu creation.

    One menu is account_menu, shown as profile menu and the other is
    main navigation used to create the breadcrumb.
    """

    def account_menu_items(self):
        """Create a personnal menu for main account page.
        Args:
            yuser (YearUser): the current user.
        Returns:
            MenuList: a single MenuList for main navigation in user app.
        
        Only used in account views.
        """
        user = self.user
        account_item = menu.MenuItem(title="Mon compte", name="account")
        colles = menu.MenuItem(title="Mes colles", name="colles",
                            display=user.teacher)
        agenda = menu.MenuItem(title="Agenda", name="agenda",
                            display=user.is_staff)
        imports = menu.MenuItem(title="Importer", name="import", display=user.is_superuser)
        corrige = menu.MenuItem(title="Corriger", name="correction", display=user.is_staff)
        groups = menu.MenuItem(title="Groupes de colles", name="collegroups",
            display=user.is_staff)
        archives = menu.MenuItem(title="Archives", name="archives", display=user.is_staff)

        menus = menu.MenuList([account_item, colles, agenda, imports, corrige, groups,
            archives],
            title="Actions")

        account_item.set_url("users:account")
        #colles.set_url("grades:colles:list")
        agenda.set_url("agenda:index")
        imports.set_url("import:index")
        #corrige.set_url("grades:bareme:list")
        groups.set_url("users:collegroups")
        #archives.set_url("archives:create")
        
        menus.id_attr = "account-menu-left"
        return menus
    
    def get_all_menus(self, context):
        """
        Return a MenuList containing all menus for current page.
        """
        return menu.MenuList()

    def get_breadcrumb(self, ctx=None):
        """
        Returns a list of MenuItem to use as breadcrumb.

        Default implementation tries to extract it from the MenuList
        returned by get_all_menus
        """
        ctx = ctx or {} # default to an empty dict
        ml = ctx.get("all_menus", [])
        bdc = [] # breadcrumb to be
        if hasattr(self, "request"):
            title = "Accueil"
            url = "/"
            home_menu = menu.MenuItem(
                title=title,
                display=True,
                url=url
            )
            home_menu.icon = "icons/home_icon.html"
            bdc.append(home_menu)
        for item in ml:
            # item can be a MenuItem or a MenuList
            if isinstance(item, menu.MenuItem):
                bdc.append(item)
            elif isinstance(item, menu.MenuList) and item.url != "":
                # marking one sub-item as current sets the MenuList.url prop
                bdc.append(item)
        return bdc

class AssetsMixin(MenuMixin):
    """
    Mixin to handle static assets and js context for views.

    Method workflow :
    setup_assets
    popns
    account_menu_items
    get_all_menus (only if "all_menus" is not a key of current context )
    get_breadcrumb
    rich_results
    """

    SCRIPTS = []
    FOOTER_SCRIPTS = []
    STYLES = [] # ["style/main.min.css"] included in setup_assets
    PRINT_STYLES = []
    PAGE_TITLE = None
    needs_latex = False
    needs_quill = False
    no_account_menu = False  # hide account menu and carret
    logger = logging.getLogger(__name__)
    # but ctx["account_menu"] is still accessible in get_all_menus

    def setup_assets(self) -> static_assets.AssetManager:
        """
        Usage :
        assets = super().setup_assets()

        and add static files to AssetManager instance and return assets.
        """
        self.assets = assets = static_assets.AssetManager()
        assets.add_scripts(*self.SCRIPTS, code=True)
        if settings.DEBUG:
            assets.add_styles("style/main.css")
        else:
            assets.add_styles("style/main.min.css")
        assets.add_styles(*self.STYLES)
        assets.add_styles(*self.PRINT_STYLES, print_style=True)
        return assets

    def _check_min_scripts(self):
        if len(self.assets.scripts) == 0 and settings.DEBUG:
            # we need structure_interraction at least
            self.logger.warning(f"No script file given, {self.__class__}")

    def popns(self, **kwargs) -> static_assets.NsData:
        """
        Returns a NsData instance.
        """
        base_ns = static_assets.NsData()
        base_ns["debug"] = {
            "INFO": settings.DEBUG,
            "WARNING": True,
        }
        return base_ns
    
    def rich_results(self, ctx):
        """
        Takes the rendering context, already populated and returns a RichResult instance
        """
        rr = rich_results.RichResults()
        bc = ctx["breadcrumb"]
        if len(bc) > 1:
            bc_list = rich_results.BreadCrumbList()
            for el in bc:
                bc_list.add_item(rich_results.BreadCrumListItem.from_MenuItem(el))
            rr.add(bc_list)
        return rr
    
    def get_page_description(self, ctx):
        return ""

    def get_page_title(self, ctx):
        return self.PAGE_TITLE

    def base_context_data(self, **kwargs):
        """
        kwargs are passed to popns.
        Defaults to get_context_data kwargs in _patch_context
        """
        ctx = {}
        assets = self.setup_assets()
        assets.update_context(ctx)
        self._check_min_scripts()
        ctx["popns"] = self.popns(**kwargs)
        if "all_menus" not in ctx:
            ctx["all_menus"] = self.get_all_menus(ctx)
        ctx["breadcrumb"] = self.get_breadcrumb(ctx)
        if self.needs_latex:
            ctx["needs_latex"] = True
        if self.needs_quill:
            ctx["needs_quill"] = True
        ctx["rich_results"] = self.rich_results(ctx)
        ctx["page_title"] = self.get_page_title(ctx)
        ctx["staff_actions"] = self.get_actions(ctx)
        ctx["page_description"] = self.get_page_description(ctx)
        return ctx
