# Spec: Agent Zero Chat Context Selector for Open Notebook

## Objective
Let the user choose which Open Notebook content Agent Zero draws on in a chat. The selector sits in the Agent Zero chat-input progress row, next to the Context gauge, and starts at notebook level. It must reach full parity with the notebook chat Context panel: per-source Off / Full text / Insights, per-insight toggles, and per-note On / Off.

User stories:
- As a user, I pick one or more notebooks for this Agent Zero chat.
- As a user, under each notebook I set every source to Off, Full text, or Insights, and toggle individual insights.
- As a user, I toggle each note On or Off.
- As a user, the selection applies to `opennotebook_chat:ask` and `opennotebook_query` for this chat without me repeating it.

## Placement
- Extension slot: `chat-input-progress-start` (rendered in `progress.html`, same row as the goal strip).
- File: `extensions/webui/chat-input-progress-start/open_notebook-context.html`.
- Shows a chip labelled `Notebooks` with a count, for example `Notebooks 2`. Hidden when the plugin is disabled.

## Drill-down
1. Notebook list: checkboxes for every notebook from `GET /api/notebooks`. Multi-select.
2. Selected notebook: expands to its sources and notes, reusing the same controls as the notebook Context panel.
3. Insights: loaded per source from `GET /api/sources/{id}/insights` when a source is set to Insights.

## Data model
```
selection = {
  notebooks: { "<notebook_id>": {
    sources: { "<source_id>": "off" | "full" | "insights" },
    insights: { "<source_id>": { "<insight_id>": true|false } },
    notes: { "<note_id>": true|false }
  } }
}
```
Defaults for a newly selected notebook: sources with insights start at Insights, others at Full text; notes On. Same defaults as the notebook panel.

## Persistence
- Keyed by Agent Zero chat context id.
- Saved browser-side (localStorage) and mirrored server-side by a plugin endpoint, so the agent-side tool can read it. Server copy lives in the chat context data, not in plugin config.
- New chat starts with no notebooks selected.

## Agent-side use
- `opennotebook_chat:ask` builds `context_config` from the selection for each selected notebook: sources map to `insights` / `full content` / `not in`; notes map to `full content` / `not in`. Per-insight toggles are sent as the Insights-mode payload built by the existing renderer.
- With no notebook selected, `ask` returns a clear message asking the user to pick notebooks in the selector. It does not fall back to all sources.
- The selection is shown as a short summary line in each `ask` response, for example `context: 2 notebooks, 14 sources, 37 notes`.

## Tokens
The backend owns token counts. The selector shows element counts only.

## Boundaries
- Always: keep the selector state per chat; send only enabled items; keep the notebook panel and this selector using the same status values.
- Ask first: changing the Agent Zero core WebUI files; changing the default when no notebook is selected.
- Never: store API keys in the selection; send a string as `context`; edit core files outside the plugin.

## Testing strategy
- Failing tests first (`tests/test_a0_context_selector.py`): slot file exists; chip markup present; notebook checkboxes, source mode buttons, insight checkboxes and note toggles present; selection-to-`context_config` mapping; no-notebook returns a message.
- Unit tests for the mapping function.
- Live check: select one notebook, set one source to Insights with one insight off, ask a question, and confirm the response summary counts match.

## Success criteria
- The chip appears in the chat-input progress row and opens the drill-down.
- Changes persist across page reload for the same chat, and are absent in a new chat.
- `opennotebook_chat:ask` uses the selection with no 422 and the summary counts match the selection.
- Full plugin test suite passes.

## Open questions
1. Server-side mirror: should I add a plugin endpoint that writes the selection to the chat context data, or should the browser pass it with each request? I recommend the endpoint.
