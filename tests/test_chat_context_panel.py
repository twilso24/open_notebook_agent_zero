import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STORE = (ROOT / 'webui' / 'open_notebook-store.js').read_text()


def test_store_loads_chat_context_insights_per_source():
    assert re.search(r'async loadChatContextInsights\s*\(', STORE), 'missing loadChatContextInsights'
    start = STORE.index('async loadChatContextInsights')
    body = STORE[start:start + 900]
    assert 'smartFetch' in body, 'insight loading must use smartFetch'
    assert '/api/sources/' in body, 'insight loading must hit the per-source endpoint'
    assert '/insights' in body, 'insight loading must hit the insights endpoint'


def test_store_exposes_chat_context_panel_state():
    assert re.search(r'chatContextInsights\s*:\s*\{\}', STORE), 'missing chatContextInsights state'
    assert re.search(r'showChatContextPanel\s*:\s*false', STORE), 'missing showChatContextPanel state'


def test_store_exposes_context_panel_toggle():
    assert re.search(r'toggleChatContextPanel\s*\(', STORE), 'missing toggleChatContextPanel'
