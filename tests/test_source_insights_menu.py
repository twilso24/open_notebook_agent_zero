"""Source menu and Insights contracts (spec: docs/specs/source-insights-menu.md)."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STORE = (ROOT / 'webui' / 'open_notebook-store.js').read_text()
PANEL = (ROOT / 'webui' / 'canvas-panel.html').read_text()


def _block(src, start_marker, end_marker):
    start = src.index(start_marker)
    return src[start : src.index(end_marker, start + len(start_marker))]


def _sources_pane():
    return _block(PANEL, 'on-tab-pane--sources', 'on-tab-pane--notes')


def _get_source_insights():
    return _block(STORE, 'async getSourceInsights(', 'async saveInsightAsNote(')


def test_existing_insights_load_without_a_selected_transformation():
    # AC1: reading existing insights must not depend on a selected preset.
    body = _get_source_insights()
    assert 'Please select a transformation first' not in body


def test_sources_tab_has_no_transformation_dropdown():
    # AC4 / R3.1: presets leave the Sources tab.
    assert 'selectedTransformationId' not in _sources_pane()


def test_generation_uses_per_source_loading_state():
    # R2.4: no global loading flag; a per-source map is used instead.
    body = _get_source_insights()
    assert 'this.loading = true' not in body
    assert 'insightsLoading' in STORE


def test_generation_posts_chosen_transformation_id():
    # R2.3: creation sends the preset the user chose.
    body = _get_source_insights()
    assert 'transformation_id' in body


def test_timeout_is_reported_to_the_user():
    # R2.6 / AC7: polling ends with a visible timeout message.
    body = _get_source_insights()
    assert 'timed out' in body.lower()


def test_insight_rows_label_with_insight_type():
    # R6.1: API returns insight_type and content, no title or name.
    assert 'insight.insight_type' in PANEL


def test_insights_panel_has_create_action():
    # R2.1 / R1.4: the create control is visible in the Insights view.
    assert 'Create insight' in PANEL


def test_row_menu_position_is_bound_to_the_viewport_or_row():
    # R5.2: the menu position value must drive the rendered style, not sit unused.
    if '_menuPos' in PANEL:
        assert re.search(r':style=[^>]*_menuPos', PANEL)
