import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CSS = (ROOT / 'webui' / 'open_notebook.css').read_text()
HTML = (ROOT / 'webui' / 'canvas-panel.html').read_text()
BLACK = {'#000', '#000000', 'black'}


def rule_body(css, selector):
    m = re.search(re.escape(selector) + r'\s*\{([^}]*)\}', css)
    assert m, 'missing CSS rule ' + selector
    return m.group(1)


def declared_color(body):
    m = re.search(r'(?<![-\w])color\s*:\s*([^;]+)', body)
    return m.group(1).strip().lower() if m else None


def button_tag_for(label):
    for m in re.finditer(r'<button\b[^>]*>.*?</button>', HTML, re.S):
        if label in m.group(0):
            return m.group(0)
    raise AssertionError('no button element contains ' + label)


def test_primary_button_text_is_black_at_rest():
    assert declared_color(rule_body(CSS, '.on-btn--primary')) in BLACK


def test_primary_button_text_stays_black_on_hover():
    assert declared_color(rule_body(CSS, '.on-btn--primary:hover')) in BLACK


def test_generate_podcast_text_is_black():
    tag = button_tag_for('Generate Podcast')
    style = re.search(r'style="([^"]*)"', tag)
    assert style, 'Generate Podcast button has no inline style'
    assert declared_color(style.group(1)) in BLACK


HEAD = (ROOT / 'extensions' / 'webui' / 'page-head' / 'open_notebook-head.html').read_text()


def test_page_head_primary_text_is_black_at_rest():
    assert declared_color(rule_body(HEAD, '.on-btn--primary')) in BLACK


def test_page_head_primary_text_stays_black_on_hover():
    assert declared_color(rule_body(HEAD, '.on-btn--primary:hover')) in BLACK


def test_page_head_on_btn_hover_does_not_override_primary():
    assert declared_color(rule_body(HEAD, '.on-btn--primary:hover')) is not None
