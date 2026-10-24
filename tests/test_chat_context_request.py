import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STORE = (ROOT / 'webui' / 'open_notebook-store.js').read_text()


def build_context_body():
    m = re.search(r'async buildChatContext\(\)\s*\{(.*?)\n    \},', STORE, re.S)
    assert m, 'buildChatContext not found'
    return m.group(1)


def test_build_chat_context_does_not_send_empty_config():
    assert 'context_config: {}' not in build_context_body()


def test_store_declares_context_selections_state():
    assert re.search(r'contextSelections\s*:\s*\{\s*sources\s*:\s*\{\s*\}\s*,\s*notes\s*:\s*\{\s*\}\s*\}', STORE)


def test_build_chat_context_sends_context_selections():
    body = build_context_body()
    assert 'context_config: this._contextConfigPayload()' in body
