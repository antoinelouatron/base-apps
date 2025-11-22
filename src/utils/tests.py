from dev.test_utils import TestCase

from utils import menu

class TestMenu(TestCase):

    def test_item_css_class(self):
        item = menu.MenuItem("item1")
        item.attrs = {"class": "custom-for-test"}
        self.assertIn("custom-for-test", item.attrs)
        item.active = True
        self.assertIn("active", item.attrs)
    
    def test_no_icon(self):
        item = menu.MenuItem("item1")
        self.assertEqual(item.icon, "")
    
    def test_set_url(self):
        item = menu.MenuItem("item1")
        item.set_url("account_login")
        self.assertEqual(item.url, "/login/")
    
    def test_submenu(self):
        item = menu.MenuItem("item1")
        item.sub_menu = ["un", "truc"]
        self.assertEqual(item.sub_menu,["un", "truc"])
        self.assertTrue(item.data["submenu"])

    def test_list_url_display(self):
        item1 = menu.MenuItem("item1", name="item1", url="None")
        item2 = menu.MenuItem("item2", name="item2")
        L = menu.MenuList([item1, item2])
        self.assertEqual(L.url, "")
        self.assertEqual(L.title, "")
        L.mark_current("item1")
        self.assertEqual(L.url, "None")
        self.assertEqual(L.title, "", "we don't change title of the list any more")
        self.assertEqual(L.id_attr(), "")
    
    def test_list_typecheck(self):
        L = menu.MenuList()
        with self.assertRaises(TypeError):
            L.append(4)
        with self.assertRaises(TypeError):
            L.extend([True])
        with self.assertRaises(TypeError):
            L = menu.MenuList(["chaine"])
    
    def test_list_methods(self):
        L = menu.MenuList()
        item1 = menu.MenuItem("item1", name="item1", url="None")
        item2 = menu.MenuItem("item2", name="item2")
        L.extend([item1, item2])
        L.append(item2)
        self.assertEqual(len(L), 2)
        L.append(menu.MenuItem("item3", name="item3"))
        L[2] = menu.MenuItem("item4", name="item4")
        with self.assertRaises(TypeError):
            L[2] = 2
        self.assertTrue(L.get("item2"), item2)
    
    def test_list_visible(self):
        item1 = menu.MenuItem("item1", name="item1", url="None")
        item2 = menu.MenuItem("item2", name="item2")
        L = menu.MenuList([item1, item2])
        L.hide("item1")
        L.hide("item2")
        self.assertEqual(list(L.visible), [])
        L.show("item1")
        self.assertEqual(list(L.visible), [item1])
        L.show("item2")
        self.assertEqual(len(list(L.visible)), 2)