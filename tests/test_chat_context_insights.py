import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STORE = (ROOT / 'webui' / 'open_notebook-store.js').read_text()


def test_store_declares_insight_selections_state():
    assert re.search(r'insightSelections\s*:', STORE), 'missing insightSelections state'


def test_store_exposes_single_insight_toggle():
    assert re.search(r'setInsightContextEnabled\s*\(', STORE), 'missing setInsightContextEnabled'


def test_renderer_includes_insights_only_for_insights_mode():
    start = STORE.index('renderChatContextText(ctx)')
    body = STORE[start:start + 2500]
    assert "mode === 'insights'" in body or "=== 'insights'" in body, 'renderer must gate insights on insights mode'


def test_renderer_filters_to_enabled_insights():
    start = STORE.index('renderChatContextText(ctx)')
    body = STORE[start:start + 2500]
    assert 'insightSelections' in body, 'renderer must filter insights by per-insight selection'


def test_insight_selections_persist_with_context_selections():
    start = STORE.index('saveContextSelections()')
    body = STORE[start:start + 600]
    assert 'insights: this.insightSelections' in body, 'save must include insightSelections'


def test_insight_selections_restore_on_load():
    start = STORE.index('loadContextSelections() {')
    body = STORE[start:start + 700]
    assert 'parsed.insights' in body, 'load must restore insightSelections'


def test_store_exposes_enabled_insights_count():
    assert re.search(r'enabledInsightsCount\s*\(', STORE) or re.search(r'get enabledInsightsCount', STORE), 'missing enabledInsightsCount'
