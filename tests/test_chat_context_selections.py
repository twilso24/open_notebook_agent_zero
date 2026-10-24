import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STORE = (ROOT / 'webui' / 'open_notebook-store.js').read_text()


def test_status_strings_match_backend_contract():
    assert "'full content'" in STORE
    assert "'not in'" in STORE
    assert "'insights'" in STORE


def test_store_persists_selections_per_notebook():
    assert re.search(r'_contextStorageKey\(\)\s*\{', STORE)
    assert 'localStorage.setItem' in STORE
    assert 'localStorage.getItem' in STORE


def test_store_restores_selections_on_notebook_select():
    m = re.search(r'async selectNotebook\(id\)\s*\{(.*?)\n    \},', STORE, re.S)
    assert m, 'selectNotebook not found'
    assert 'loadContextSelections' in m.group(1)


def test_store_exposes_bulk_and_single_setters():
    for fn in ['setSourceContextMode', 'setNoteContextMode', 'applyBulkSourceContext', 'applyBulkNoteContext']:
        assert re.search(fn + r'\s*\(', STORE), fn


def test_store_counts_getter_names_match_spec():
    for name in ['sourcesInsightsCount', 'sourcesFullCount', 'notesIncludedCount']:
        assert name in STORE, name
