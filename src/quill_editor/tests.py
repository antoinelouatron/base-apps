from datetime import date
from django.core.exceptions import ImproperlyConfigured
from django.utils.functional import lazystr

from dev.test_utils import TestCase
from quill_editor import widgets
from quill_editor.forms import QuillFormField
from quill_editor.sanitize import clean_quill_html

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


class TestSanitize(TestCase):

    def test_empty(self):
        self.assertEqual(clean_quill_html(""), "")
        self.assertIsNone(clean_quill_html(None))

    def test_keeps_allowed_formatting(self):
        html = "<p><strong>g</strong> <em>i</em> <u>u</u></p><blockquote>q</blockquote>"
        self.assertEqual(clean_quill_html(html), html)

    def test_strips_script(self):
        out = clean_quill_html("<p>ok</p><script>alert(1)</script>")
        self.assertNotIn("<script>", out)
        self.assertIn("<p>ok</p>", out)

    def test_strips_event_handler(self):
        out = clean_quill_html('<img src=x onerror="alert(1)">')
        self.assertNotIn("onerror", out)
        self.assertNotIn("<img", out)

    def test_strips_javascript_url(self):
        out = clean_quill_html('<a href="javascript:alert(1)">x</a>')
        self.assertNotIn("javascript:", out)
        self.assertIn(">x</a>", out)

    def test_keeps_safe_link(self):
        out = clean_quill_html(
            '<a href="https://example.org" target="_blank" rel="noopener">l</a>')
        self.assertIn('href="https://example.org"', out)
        self.assertIn('target="_blank"', out)
        self.assertIn('rel="noopener"', out)

    def test_strips_disallowed_tags(self):
        out = clean_quill_html("<h1>t</h1><table><tr><td>x</td></tr></table>")
        self.assertNotIn("<h1>", out)
        self.assertNotIn("<table>", out)
        # text content is preserved
        self.assertIn("t", out)
        self.assertIn("x", out)

    def test_formula_reduced_to_source(self):
        html = ('<span class="ql-formula" data-value="\\frac12">'
                '<span class="katex"><span class="katex-mathml">junk</span></span>'
                '</span>')
        out = clean_quill_html(html)
        # rendered KaTeX subtree removed, LaTeX source kept
        self.assertNotIn("katex", out)
        self.assertNotIn("junk", out)
        self.assertIn('data-value="\\frac12"', out)
        self.assertIn('class="ql-formula"', out)

    def test_code_block_with_highlight_preserved(self):
        html = ('<div class="ql-code-block-container" spellcheck="false">'
                '<div class="ql-code-block" data-language="python">'
                '<span class="hljs-keyword">def</span> f():</div></div>')
        self.assertEqual(clean_quill_html(html), html)

    def test_idempotent(self):
        html = ('<p><strong>x</strong></p>'
                '<span class="ql-formula" data-value="a^2"><span class="katex">r</span></span>'
                '<script>alert(1)</script>')
        once = clean_quill_html(html)
        self.assertEqual(clean_quill_html(once), once)

    def test_form_field_clean_sanitizes(self):
        field = QuillFormField(required=False)
        out = field.clean("<p>hi</p><script>alert(1)</script>")
        self.assertNotIn("<script>", out)
        self.assertIn("<p>hi</p>", out)