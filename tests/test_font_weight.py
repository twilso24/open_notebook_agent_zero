import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FILES = [
    ROOT / 'webui' / 'open_notebook.css',
    ROOT / 'extensions' / 'webui' / 'page-head' / 'open_notebook-head.html',
]
REGULAR = {'400', 'normal'}


def rules_for(text, selector):
    return re.findall(re.escape(selector) + r'\s*\{([^}]*)\}', text)


def weights(body):
    return re.findall(r'font-weight\s*:\s*([^;]+)', body)


def test_primary_button_label_is_regular_weight():
    for f in FILES:
        for body in rules_for(f.read_text(), '.on-btn--primary'):
            for w in weights(body):
                assert w.strip().lower() in REGULAR, f.name


def test_notebook_title_is_regular_weight():
    for f in FILES:
        for body in rules_for(f.read_text(), '.on-card__title'):
            for w in weights(body):
                assert w.strip().lower() in REGULAR, f.name
