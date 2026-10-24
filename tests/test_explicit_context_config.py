"""Contract: an empty selection must never mean 'include everything'.

The notebook backend treats an empty context_config as 'include all sources'.
The grounding hook and the ask tool must therefore send an explicit status for
every known source and note id.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

import sys

sys.path.insert(0, str(ROOT))

from tools.context_selection import (  # noqa: E402
    selection_to_explicit_context_config,
    context_config_has_included,
)


def test_unselected_sources_become_not_in():
    cfg = selection_to_explicit_context_config(
        {"sources": {"s1": "full"}, "notes": {}}, ["s1", "s2", "s3"], []
    )
    assert cfg["sources"] == {
        "s1": "full content",
        "s2": "not in",
        "s3": "not in",
    }


def test_empty_selection_is_all_not_in_and_has_nothing_included():
    cfg = selection_to_explicit_context_config({}, ["s1", "s2"], ["n1"])
    assert cfg["sources"] == {"s1": "not in", "s2": "not in"}
    assert cfg["notes"] == {"n1": "not in"}
    assert context_config_has_included(cfg) is False


def test_notes_are_explicit_too():
    cfg = selection_to_explicit_context_config(
        {"sources": {"s1": "off"}, "notes": {"n1": True}}, ["s1"], ["n1", "n2"]
    )
    assert cfg["notes"] == {"n1": "full content", "n2": "not in"}


def test_insights_mode_maps_and_counts_as_included():
    cfg = selection_to_explicit_context_config({"sources": {"s1": "insights"}}, ["s1"], [])
    assert cfg["sources"]["s1"] == "insights"
    assert context_config_has_included(cfg) is True


def test_unknown_source_ids_from_selection_are_kept():
    cfg = selection_to_explicit_context_config({"sources": {"legacy": "full"}}, ["s1"], [])
    assert cfg["sources"]["legacy"] == "full content"
    assert cfg["sources"]["s1"] == "not in"


def test_grounding_hook_uses_explicit_config_and_fetches_ids():
    src = (
        ROOT / "extensions" / "python" / "system_prompt" / "_20_notebook_grounding.py"
    ).read_text()
    assert "selection_to_explicit_context_config" in src
    assert "/api/sources?notebook_id=" in src
    assert "context_config_has_included" in src


def test_store_commits_defaults_to_server():
    src = (ROOT / "webui" / "a0-context-store-v2.js").read_text()
    start = src.index("async loadNotebookData(nbId) {")
    body = src[start : src.index("async loadInsights(", start)]
    assert "commit()" in body, "defaults must be mirrored, an empty mirror means include-all"
