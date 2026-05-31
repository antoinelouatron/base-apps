"""
Server-side sanitization of Quill 2.x HTML output.

The stored content is the editor's ``root.innerHTML``, which contains the
*rendered* embeds (full KaTeX subtree, highlight.js spans, ...). We never trust
that markup: an attacker can POST arbitrary HTML bypassing the editor.

Strategy:
 1. Reduce every ``span.ql-formula`` to its source only (the ``data-value``
    LaTeX attribute), dropping the rendered KaTeX subtree. KaTeX re-renders from
    ``data-value`` (in the editor automatically, on read-only pages via a small
    render pass). This keeps the allowlist minimal and avoids whitelisting
    MathML + inline styles.
 2. Allowlist-sanitize the rest with bleach (drops scripts, event handlers,
    dangerous protocols, and any tag/attribute not needed by the "default"
    Quill config).

This runs only on QuillField content (via QuillFormField.clean). It never
touches other HTML on the site (e.g. separately stored pre-rendered KaTeX).

Allowlist is derived from QUILL_CONFIGS["default"]: bold, italic, underline,
blockquote, link, code-block (+highlight.js) and formula.
"""
import bleach
from bs4 import BeautifulSoup

ALLOWED_TAGS = [
    "p", "br",
    "strong", "em", "u",
    "blockquote",
    "a",
    # code-block: Quill 2 renders nested <div>s; <pre> covers getSemanticHTML()
    "div", "pre",
    # formula placeholder + highlight.js tokens
    "span",
]

ALLOWED_ATTRIBUTES = {
    "a": ["href", "target", "rel"],
    "div": ["class", "data-language", "spellcheck"],
    "pre": ["class", "data-language", "spellcheck"],
    "span": ["class", "data-value"],
}

ALLOWED_PROTOCOLS = ["http", "https", "mailto"]


def clean_quill_html(html: str) -> str:
    """
    Sanitize Quill 2.x HTML for safe storage/display.

    Idempotent: re-cleaning already-clean content is a no-op.
    """
    if not html:
        return html
    # 1. Reduce formulas to their source. ``clear()`` removes the rendered
    # KaTeX children while keeping the tag and its data-value attribute.
    soup = BeautifulSoup(html, "html.parser")  # fragment parser, no html/body wrapper
    for formula in soup.select("span.ql-formula"):
        formula.clear()
    html = str(soup)

    # 2. Allowlist sanitize.
    return bleach.clean(
        html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        protocols=ALLOWED_PROTOCOLS,
        strip=True,
    )