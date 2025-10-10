from datetime import date
from django.core.exceptions import ImproperlyConfigured
from django.utils.functional import lazystr

from dev.test_utils import TestCase
from quill_editor import widgets

class TestWidget(TestCase):

    def test_base_creation(self):
        wid = widgets.QuillWidget()
        self.assertEqual(wid.config, widgets.DEFAULT_CONFIG)
        self.assertNotEqual(wid.render("name", "value", attrs={"id": "id"}), "")
    
    def test_bad_config(self):
        with self.assertRaises(ImproperlyConfigured):
            widgets.QuillWidget(config_name="bad")
        # not a mapping
        QUILL_CONFIGS = "bad"
        with self.assertRaises(ImproperlyConfigured):
            with self.settings(QUILL_CONFIGS=QUILL_CONFIGS):
                widgets.QuillWidget()
        # not a mapping
        QUILL_CONFIGS = {"default": "bad"}
        with self.assertRaises(ImproperlyConfigured):
            with self.settings(QUILL_CONFIGS=QUILL_CONFIGS):
                widgets.QuillWidget()
    
    def test_lazy_config(self):
        QUILL_CONFIGS = {"default": {"theme": lazystr("bubble"), "date": date.today()}}
        with self.settings(QUILL_CONFIGS=QUILL_CONFIGS):
            wid = widgets.QuillWidget()
            self.assertEqual(wid.config["theme"], "bubble")
            wid.render("name", "value", attrs={"id": "id"})