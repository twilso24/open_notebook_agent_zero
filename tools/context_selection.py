"""
Open Notebook Plugin - Chat Context Selection Mapping

Converts the Agent Zero chat context selector state into the context_config
payload the Open Notebook backend accepts.

Selector state per notebook:
    {
      "<notebook_id>": {
        "sources": {"<source_id>": "off" | "full" | "insights"},
        "insights": {"<source_id>": {"<insight_id>": true|false}},
        "notes": {"<note_id>": true|false}
      }
    }

Backend status values:
    sources: insights | full content | not in
    notes:   full content | not in
"""

SOURCE_STATUS = {
    "off": "not in",
    "full": "full content",
    "insights": "insights",
}

NOTE_STATUS = {
    "on": "full content",
    "off": "not in",
}

CONTEXT_DATA_KEY = "open_notebook_context_selection"


def selection_to_context_config(selection: dict) -> dict:
    """Map one notebook's selector state to a context_config dictionary."""
    if not isinstance(selection, dict):
        return {}

    sources = {}
    for source_id, mode in (selection.get("sources") or {}).items():
        status = SOURCE_STATUS.get(str(mode))
        if status:
            sources[str(source_id)] = status

    notes = {}
    for note_id, enabled in (selection.get("notes") or {}).items():
        if isinstance(enabled, bool):
            notes[str(note_id)] = NOTE_STATUS["on" if enabled else "off"]
        else:
            status = NOTE_STATUS.get(str(enabled))
            if status:
                notes[str(note_id)] = status

    config = {}
    if sources:
        config["sources"] = sources
    if notes:
        config["notes"] = notes
    return config


def selected_insight_ids(selection: dict, source_id: str) -> set:
    """Return the enabled insight ids for one source."""
    if not isinstance(selection, dict):
        return set()
    mapping = (selection.get("insights") or {}).get(source_id) or {}
    return {str(k) for k, v in mapping.items() if v}


def summarize_selection(notebooks: dict) -> dict:
    """Count notebooks, included sources, insights-mode sources and included notes."""
    nb_count = 0
    source_count = 0
    insight_source_count = 0
    note_count = 0

    for state in (notebooks or {}).values():
        if not isinstance(state, dict):
            continue
        nb_count += 1
        for mode in (state.get("sources") or {}).values():
            if mode == "full":
                source_count += 1
            elif mode == "insights":
                insight_source_count += 1
        for enabled in (state.get("notes") or {}).values():
            if enabled is True or enabled == "on":
                note_count += 1

    return {
        "notebooks": nb_count,
        "sources": source_count,
        "insight_sources": insight_source_count,
        "notes": note_count,
    }


def summary_line(notebooks: dict) -> str:
    """Human-readable one-line summary for tool responses."""
    s = summarize_selection(notebooks)
    parts = [f"{s['notebooks']} notebook(s)"]
    if s["sources"]:
        parts.append(f"{s['sources']} full source(s)")
    if s["insight_sources"]:
        parts.append(f"{s['insight_sources']} insights source(s)")
    parts.append(f"{s['notes']} note(s)")
    return "context: " + ", ".join(parts)
