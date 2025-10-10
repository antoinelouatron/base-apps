"""
date: 2024-03-01
"""
import types
from django.contrib.auth import get_user_model

from dev.test_utils import TestCase
from utils import menu, views
from utils.views.static_assets import NsData, AssetManager
from utils.views import rich_results, formset_form_views


class TestNsData(TestCase):

    def test_init(self):
        ns = NsData(("a", 1), ("b", 2))
        self.assertEqual(ns["a"], 1)
        self.assertEqual(ns["b"], 2)
        ns.extend([("a", 4), ("c", 12)])
        self.assertEqual(ns["a"], 4)
        self.assertEqual(len(ns), 3)
        self.assertTrue("a" in ns)
    
    def test_bool(self):
        ns = NsData()
        self.assertFalse(ns)
        ns["a"] = 1
        self.assertTrue(ns)
        del ns["a"]
        self.assertFalse(ns)

    def test_setitem(self):
        ns = NsData()
        ns["a"] = 1
        self.assertEqual(ns["a"], 1)
        with self.assertRaises(ValueError):
            ns["a.a"] = 1
        with self.assertRaises(ValueError):
            ns["a"] = {"a": 1}
        ns["b"] = {"a":  {"a": 1}}
        self.assertEqual(ns["b.a.a"], 1)
        self.assertTrue("b.a.a" in ns)
        # set another value in same namespace
        ns["b.a.b"] = 7
        self.assertEqual(ns["b.a.b"], 7)
        self.assertEqual(ns["b.a.a"], 1)  # previous value has not changed
        del ns["a"]
        ns["a.a"] = 1
        self.assertEqual(len(ns), 3)
        ns.warning = lambda t: self.assertEqual(t[1], 2)
        ns["b.a.b"] = 2
    
    def test_setitem_errors(self):
        ns = NsData()
        with self.assertRaises(TypeError):
            ns[1] = 2
        ns["a"] = {"a": {"b": 1}, 1:2}
        with self.assertRaises(ValueError):
            ns["a.a"] = 2
    
    def test_empty_dict_value(self):
        ns = NsData()
        ns["a"] = {}
        self.assertEqual(ns["a"], {})
        ns["a.b"] = 1
        self.assertEqual(ns["a.b"], 1)
        ns["b"] = {"c": {}}
        self.assertEqual(ns["b.c"], {})
        ns["b.c.d"] = 2
        self.assertEqual(ns["b.c.d"], 2)

    def test_bool(self):
        ns = NsData()
        self.assertFalse(ns)
        ns["a"] = 1
        self.assertTrue(ns)
        del ns["a"]
        self.assertFalse(ns)

    def test_iteration(self):
        ns = NsData()
        ns["a.a"] = 1
        ns["b"] = {"a":  {"a": 1, "b": 1}}
        self.assertEqual(set(ns.keys()), {"a.a", "b.a.a", "b.a.b"})
        self.assertEqual(set(ns.values()), {1})
    
    def test_deletion(self):
        ns = NsData()
        ns["a"] = 1
        self.assertIn("a", ns)
        del ns["a"]
        self.assertNotIn("a", ns)
        with self.assertRaises(TypeError):
            del ns[1]
        with self.assertRaises(KeyError):
            del ns["a"]
        with self.assertRaises(KeyError):
            del ns["a.a"]
        ns["a.a"] = 1
        del ns["a.a"]
        with self.assertRaises(KeyError):
            ns["a.a"]
    
    def test_data(self):
        ns = NsData()
        ns["a.a"] = 1
        ns["b"] = {"a":  {"a": 1, "b": 1}}
        data = ns.data
        self.assertEqual(data, {"a": {"a": 1}, "b": {"a": {"a": 1, "b": 1}}})
    
    def test_repr(self):
        ns = NsData()
        ns["a.a"] = 1
        ns2 = eval(repr(ns))
        self.assertEqual(ns.data, ns2.data)
    
    def test_exceptions(self):
        ns = NsData()
        self.assertRaises(ValueError, ns.append, (1,2,3))
        with self.assertRaises(TypeError):
            ns[1] = 2
        with self.assertRaises(TypeError):
            ns[1]
        with self.assertRaises(KeyError):
            ns["a"]
        ns["a.a"] = 1
        with self.assertRaises(ValueError):
            ns["a.a.b"] = 1
    
    def test_rendering(self):
        ns = NsData()
        html = ns.render()
        self.assertEqual(html, "")
        ns["a"] = "une chaine"
        ns["b"] = True
        html = ns.render()
        self.assertNotEqual(html, "")

        
class TestAssets(TestCase):

    def test_add(self):
        assets = AssetManager()
        assets.add_scripts("a", "b", "c")
        self.assertEqual(len(assets.scripts), 3)
        assets.add_styles("a", "b", "c")
        self.assertEqual(len(assets.styles), 3)
    
    def test_replace(self):
        assets = AssetManager()
        assets.add_scripts("a", "b", "c")
        self.assertEqual(len(assets.scripts), 3)
        assets.replace_script("d", "c")
        self.assertEqual(len(assets.scripts), 3)
        assets.replace_script("c", "c")
        self.assertEqual(len(assets.scripts), 4)
        assets.replace_style("a", print_style=True)
        self.assertEqual(len(assets.print_styles), 1)
    
    def test_context(self):
        assets = AssetManager()
        ctx = {}
        assets.update_context(ctx)
        for name in ("style_list", "print_styles", "script_list"):
            self.assertIn(name, ctx)
    
    def test_worker_url(self):
        assets = AssetManager()
        assets.add_worker("", "worker.js")
        self.assertEqual(len(assets.worker_urls()), 1)
    
    def test_with_code(self):
        assets = AssetManager()
        assets.add_scripts("_non_existing_", code=True)
        self.assertEqual(len(assets.scripts), 0)

class TestRichResults(TestCase):

    def test_site(self):
        item = rich_results.ListItem()
        self.assertIsNotNone(item.domain)
    
    def test_lists(self):
        L = rich_results.ItemList()
        N = 3
        for k in range(N):
            item = rich_results.ListItem(data={"number": k})
            L.add_item(item)
            self.assertEqual(len(L), k+1)
        d = L.as_dict()
        self.assertIn("@context", d, "standalone")
        self.assertIn("itemListElement", d)
        self.assertEqual(len(d["itemListElement"]), N)
    
    def test_list_creation(self):
        L = rich_results.ItemList(
            [rich_results.ListItem(data={"number": k}) for k in range(3)])
        self.assertEqual(len(L), 3)
        for k in range(3):
            self.assertEqual(L.data["itemListElement"][k]["position"], k+1)
    
    def test_breadcrumb(self):
        menu_item = menu.MenuItem("My item", "home/", True, name="item1")
        item = rich_results.BreadCrumListItem.from_MenuItem(menu_item)
        d = item.as_dict()
        self.assertIn("item", d)
        self.assertIn("name", d)
        self.assertEqual(d["@type"], "ListItem")
    
    def test_course(self):
        course = rich_results.CourseItem()
        self.assertEqual(course.type, "Course")
        def chap():
            pass # dummy object, not called
        chap.title = "1"
        chap.description = ""
        chap.get_absolute_url = lambda : "1"
        course = rich_results.CourseItem.from_Chapter(chap)
        self.assertEqual(course.data["name"], "1")
        self.assertNotIn("url", course.data)
        course = rich_results.CourseItem.from_Chapter(chap, standalone=False)
        self.assertEqual(course.data["name"], "1")
        self.assertIn("url", course.data)
    
    def test_results(self):
        rr = rich_results.RichResults()
        self.assertFalse(rr)
        self.assertEqual(str(rr), "")
        rr.add(rich_results.ItemList())
        self.assertTrue(rr)
        s = str(rr)
        self.assertFalse(s.startswith("["))
        self.assertFalse(s.endswith("]"))
        rr.add(rich_results.ItemList())
        self.assertTrue(rr)
        s = str(rr)
        self.assertTrue(s.startswith("["))
        self.assertTrue(s.endswith("]"))


class TestMixins(TestCase):

    def test_menu_mixin(self):
        class DummyView(views.TemplateView):
            template_name = "base.html"

            def get_all_menus(self, ctx):
                return [
                    menu.MenuItem("Home", "home/", True, name="home"),
                    menu.MenuList([
                        menu.MenuItem("Item 1", "item1/", True, name="item1"),
                        menu.MenuItem("Item 2", "item2/", True, name="item2"),
                    ])
                ]
        
        view = DummyView()
        request = types.SimpleNamespace(
            session={},
            user=get_user_model()(username="foo"),
            method="get",
            COOKIES={},
            META={},)
        view.setup(request)
        ctx = view.get_context_data()
        self.assertIn("all_menus", ctx)
        self.assertIn("breadcrumb", ctx)
        self.assertEqual(len(ctx["breadcrumb"]), 2)

        class DummyView2(DummyView):

            def get_all_menus(self, ctx):
                ml = super().get_all_menus(ctx)
                ml[1].mark_current("item1")
                return ml
        view2 = DummyView2()
        view2.setup(request)
        ctx2 = view2.get_context_data()
        self.assertIn("all_menus", ctx2)
        self.assertIn("breadcrumb", ctx2)
        self.assertEqual(len(ctx2["breadcrumb"]), 3)
    
    def test_asset_mixin(self):
        class DummyView(views.TemplateView):
            template_name = "base.html"

        
        view = DummyView()
        request = types.SimpleNamespace(
            session={},
            user=get_user_model()(username="foo"),
            method="get",
            COOKIES={},
            META={},)
        view.setup(request)
        ctx = view.get_context_data()
        self.assertIn("style_list", ctx)
        self.assertIn("script_list", ctx)
        self.assertIn("print_styles", ctx)
        self.assertIn("style/main.min.css", ctx["style_list"])
        with self.settings(DEBUG=True):
            ctx = view.get_context_data()
            self.assertIn("style/main.css", ctx["style_list"])
        
    
    def test_improperly_configured(self):
        # no formset_fields
        class DummyView(formset_form_views.CreateView):
            model = get_user_model()
            fields = ["username"]
            formset_model = get_user_model()
            template_name = "base.html"
        
        with self.assertRaises(formset_form_views.ImproperlyConfigured):
            view = DummyView.as_view()
            request = types.SimpleNamespace(
                session={},
                method="get",
                COOKIES={},
                META={},)
            view(request)
    
    def test_config_conflict(self):
        class DummyView(formset_form_views.CreateView):
            model = get_user_model()
            fields = ["username"]
            formset_model = get_user_model()
            formset_fields = ["username"]
            formset_class = "un truc"
        
        with self.assertRaises(formset_form_views.ImproperlyConfigured):
            view = DummyView.as_view()
            request = types.SimpleNamespace(
                session={},
                method="get",
                COOKIES={},
                META={},)
            view(request)
    
    def test_config_ok(self):
        class DummyView(formset_form_views.CreateView):
            model = get_user_model()
            fields = ["username"]
            formset_model = get_user_model()
            formset_fields = ["username"]
            template_name = "base.html"
        
        view = DummyView.as_view()
        request = types.SimpleNamespace(
            session={},
            user=get_user_model()(username="foo"),
            method="get",
            COOKIES={},
            META={},)
        resp = view(request)
        self.assertEqual(resp.status_code, 200)
        # check logging warning when in debug mode
        with self.settings(DEBUG=True):
            with self.assertLogs(level="WARNING"):
                view(request)
    
    def test_model_by_queryset(self):
        class DummyView(formset_form_views.CreateView):
            model = get_user_model()
            fields = ["username"]
            formset_fields = ["username"]
            template_name = "base.html"
            
            def get_formset_queryset(self):
                return get_user_model().objects.all()
        
        view = DummyView.as_view()
        request = types.SimpleNamespace(
            session={},
            user=get_user_model()(username="foo"),
            method="get",
            COOKIES={},
            META={},)
        resp = view(request)
        self.assertEqual(resp.status_code, 200)