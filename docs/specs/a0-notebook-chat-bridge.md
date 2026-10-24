# Spec: Agent Zero to Open Notebook Chat Bridge

## Objective
Let Agent Zero answer questions about an Open Notebook notebook using the notebook's own sources, insights and notes as grounded context, without spending the notebook's LLM tokens on every turn.

User stories:
- As a user, I ask Agent Zero a question about a notebook and get an answer grounded in that notebook's sources.
- As a user, I choose which notebook, and optionally which sources or notes, the answer draws from.
- As a user, I continue a previous notebook conversation by session.

## Contract (verified against the live backend)
- Create session: `POST /api/chat/sessions` with `notebook_id`.
- Build context: `POST /api/chat/context` with `notebook_id` and `context_config` (`sources` and `notes` maps of status; sources: `insights` | `full content` | `not in`; notes: `full content` | `not in`).
- Execute: `POST /api/chat/execute` with `session_id`, `message`, `context` (JSON object, not a string, else HTTP 422), optional `model_override`.
- Read history: `GET /api/chat/sessions/{session_id}`.

## Design
- New agent tool `opennotebook_chat` in `tools/opennotebook_chat.py`, following the pattern of `opennotebook_query`.
- Actions: `ask` (notebook_id, message, optional session_id, optional context_config), `history` (session_id), `new_session` (notebook_id).
- `ask` without a session creates one; the returned response includes the session_id so follow-ups can continue it.
- Default context: all sources at `full content`, all notes at `full content`, unless `context_config` overrides.
- Notebook IDs may be given by name; resolve through the existing `resolve_notebook_id` helper.
- Requests go through the existing client (`client.py`) so host, auth and error handling match other tools.
- Prompt file `prompts/default/agent.system.tool.opennotebook_chat.md` documents usage for the agent.

## Boundaries
- Always: resolve and verify the notebook before asking; return the session_id; surface backend errors verbatim with status code.
- Ask first: deleting chat sessions; changing the default context scope; using a model_override.
- Never: send a string as `context`; invent source or note IDs; store API keys in tool args.

## Testing strategy
- Unit tests for request-body construction (context is an object, context_config mapping) in `tests/test_chat_bridge.py`, written before the tool.
- Live smoke test: ask one question against the Open Notebook notebook and check the answer cites its sources.

## Success criteria
- `opennotebook_chat:ask` returns an answer plus session_id for notebook `📓 Open Notebook`.
- A follow-up with that session_id keeps prior context.
- Invalid notebook or session returns a clear error, not a 500.
- Request bodies match the verified contract (no HTTP 422 on execute).

## Decisions (confirmed by user)
1. Context selection: A0 uses the same context menu as the chat-window Context panel (per-source Off / Full text / Insights, per-insight toggles, note On/Off). `context_config` mirrors that menu's state for the notebook. Default when no menu state exists: the notebook's stored selection, else the panel defaults.
2. Answers: return the full answer text, plus the session_id.
3. Scope: chat and search. `search` action wraps `GET /api/search` for notebook-scoped lookup.

## Plan
- Phase 1: failing tests for request-body construction and context_config mapping.
- Phase 2: `tools/opennotebook_chat.py` with actions `ask`, `history`, `new_session`, `search`.
- Phase 3: prompt file `prompts/default/agent.system.tool.opennotebook_chat.md`.
- Phase 4: live smoke test against 📓 Open Notebook.
