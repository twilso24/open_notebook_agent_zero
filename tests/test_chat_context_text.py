import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STORE = (ROOT / 'webui' / 'open_notebook-store.js').read_text()


def test_store_renders_context_text_function():
    assert re.search(r'renderChatContextText\s*\(', STORE), 'missing renderChatContextText'


def test_rendered_context_uses_backend_headings():
    assert '## SOURCE CONTENT' in STORE
    assert '## SOURCE INSIGHTS' in STORE


def test_rendered_context_uses_backend_id_labels():
    assert '**Source ID:**' in STORE
    assert '**Insight ID:**' in STORE


def test_send_body_uses_built_context_object():
    start = STORE.index('async sendChatMessage')
    body = STORE[start:start + 1500]
    assert 'context: this.buildChatContextPayload(' in body, 'execute body must send the built context object'
    assert 'context: this.renderChatContextText(' not in body, 'execute body must not send rendered text'
