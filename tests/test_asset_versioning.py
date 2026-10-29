"""Asset versioning contract for the Open Notebook canvas surface.

The panel is loaded through a versioned modal URL, but it imports its Alpine
store over a bare path. The service worker caches backend assets by request
URL, so an unversioned import can keep serving stale store JS to a client whose
panel HTML has already moved on. When that skew happens the panel calls store
methods that the cached JS does not define, the tap throws, and no row menu
opens at all (the mobile-only symptom).

Both assets must move together.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PANEL = ROOT / "webui" / "canvas-panel.html"
REGISTER = ROOT / "extensions" / "webui" / "right_canvas_register_surfaces" / "register-open_notebook.js"


def _panel_version():
    text = REGISTER.read_text()
    match = re.search(r"canvas-panel\.html\?v=([\w.\-]+)", text)
    assert match, "panel modal path must carry a version query"
    return match.group(1)


def _store_import_version():
    text = PANEL.read_text()
    match = re.search(r"open_notebook-store\.js(?:\?v=([\w.\-]+))?\"", text)
    assert match, "panel must import the store script"
    return match.group(1)


def test_store_import_is_versioned():
    version = _store_import_version()
    assert version, (
        "the store import must carry a ?v= query; an unversioned import lets the "
        "service worker serve stale store JS to a client with newer panel HTML"
    )


def test_store_import_version_matches_panel_version():
    panel_version = _panel_version()
    store_version = _store_import_version()
    assert store_version == panel_version, (
        f"panel is at v={panel_version} but the store import is at v={store_version}; "
        "version skew makes _openRowMenu undefined and the row menu never opens"
    )
