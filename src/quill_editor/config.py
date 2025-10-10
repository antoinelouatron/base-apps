import core.base_settings as base
DEFAULT_CONFIG = base.QUILL_CONFIGS["default"]

MEDIA_JS = [
    # syntax-highlight
    "https://cdnjs.cloudflare.com/ajax/libs/highlight.js/10.1.1/highlight.min.js",
    # quill
    "js/vendor/quill.min.js",
    # custom
    "js/quill_editor/quill_editor.js",
    "https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-chtml.js"
]
MEDIA_CSS = [
    # syntax-highlight
    "style/quill.snow.css",
    "https://cdnjs.cloudflare.com/ajax/libs/highlight.js/10.1.1/styles/darcula.min.css",
    # custom
]