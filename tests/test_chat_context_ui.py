import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PANEL = (ROOT / 'webui' / 'canvas-panel.html').read_text()


def _region(start_marker, end_marker):
    start = PANEL.index(start_marker)
    end = PANEL.index(end_marker, start)
    return PANEL[start:end]

SOURCES = _region("activeTab === 'sources'", "activeTab === 'notes'")
NOTES = _region("activeTab === 'notes'", "activeTab === 'podcasts'")
CHAT = PANEL[PANEL.index("activeTab === 'chat'"):]


def test_sources_tab_has_no_context_control():
    assert 'applyBulkSourceContext' not in SOURCES
    assert 'Chat context:' not in SOURCES


def test_notes_tab_has_no_context_control():
    assert 'applyBulkNoteContext' not in NOTES
    assert 'Chat context:' not in NOTES


def test_chat_window_has_context_panel():
    assert 'on-chat-context-panel' in CHAT


def test_chat_panel_has_source_mode_and_insight_controls():
    assert 'setSourceContextMode(' in CHAT
    assert 'setInsightContextEnabled(' in CHAT


def test_chat_panel_has_note_toggles():
    assert 'setNoteContextMode(' in CHAT


def test_chat_footer_shows_element_counts():
    assert 'enabledInsightsCount' in CHAT
    assert 'sourcesFullCount' in CHAT
    assert 'notesIncludedCount' in CHAT


def test_chat_footer_has_no_token_count():
    assert 'token_count' not in CHAT


def test_chat_window_has_panel_toggle_button():
    assert 'toggleChatContextPanel(' in CHAT
