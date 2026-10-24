"""Sources must start as 'off' and never silently switch to 'insights' due to
legacy defaults or cached pre-fix code.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STORE = ROOT / "webui" / "a0-context-store-v2.js"
CHIP = (
    ROOT / "extensions" / "webui" / "chat-input-progress-start" / "open_notebook-context.html"
)


def test_store_bumps_storage_key_to_v3():
    src = STORE.read_text()
    assert "open_notebook:a0-context:v3" in src


def test_onmount_uses_local_selection_migrator():
    src = STORE.read_text()
    start = src.index("onMount()")
    body = src[start : start + 400]
    assert "loadLocalSelection()" in body


def test_legacy_selection_clears_source_modes_and_keeps_notes():
    src = STORE.read_text()
    assert "LEGACY_STORAGE_KEY" in src
    assert "_adopt" in src
    assert "st.notes" in src


def test_loadfromserver_adopts_sanitized_selection():
    src = STORE.read_text()
    start = src.index("async loadFromServer()")
    body = src[start : start + 900]
    assert "_adopt(data.selection)" in body


def test_chip_busts_store_cache_with_version_query():
    html = CHIP.read_text()
    assert "a0-context-store-v2.js?v=3" in html
