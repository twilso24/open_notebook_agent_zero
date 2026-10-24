"""The canvas store must not default new sources to 'insights' or 'full'. Notes may still default on."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STORE = ROOT / "webui" / "open_notebook-store.js"


def _sources_block() -> str:
    src = STORE.read_text()
    start = src.index("applyContextDefaults() {")
    body = src[start : src.index("setSourceContextMode(", start)]
    s = body.index("for (const src of")
    return body[s : body.index("for (const note of", s)]


def test_new_sources_default_to_off_not_insights():
    block = _sources_block()
    assert "'insights'" not in block, "sources must not default to insights"
    assert "'full'" not in block, "sources must not default to full"
    assert "sel.sources[src.id] = 'off'" in block
