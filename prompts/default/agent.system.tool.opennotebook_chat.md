### opennotebook_chat:
chat with an Open Notebook notebook using the notebook's own chat engine

**Actions:**

- `ask` — Send a message to a notebook chat. Creates a chat session automatically when none is given. Returns the full answer plus the session id so follow-ups can continue the same conversation.
- `history` — Read all messages of an existing chat session.
- `new_session` — Start a fresh chat session for a notebook.
- `search` — Search notebook content (sources and notes) for a query.

**Parameters:**
- `notebook_id` (string, required for ask/new_session/search) — The notebook to use; notebook names may be accepted when the tool resolves them internally
- `message` (string, required for ask) — The message to send to the notebook chat
- `session_id` (string, optional for ask, required for history) — An existing chat session id; omit to start a new session
- `context_config` (object, optional for ask) — Context selection matching the chat panel: `{sources: {<source_id>: "insights" | "full content" | "not in"}, notes: {<note_id>: "full content" | "not in"}}`. Omit to use the notebook's defaults.
- `query` (string, required for search) — The search text

**When to use:**
- User asks a question about a notebook's content → use `ask` (e.g. "ask the Open Notebook notebook how sources are processed" or "what does the API reference say about context?").
- User asks to continue a previous notebook conversation → use `ask` with the `session_id` from the earlier answer.
- User asks what a previous chat discussed → use `history` with a `session_id`.
- User wants to find content in a notebook → use `search`.

**Important:**
- The notebook chat answers only from the notebook's sources and notes, so prefer `ask` over answering from general knowledge when the user wants notebook-grounded information.
- `context_config` mirrors the context panel in the chat window: sources can be off, full text, or insights; notes can be on or off.

usage:
~~~json
{
    "thoughts": ["User wants to ask the Open Notebook notebook about its API contract."],
    "headline": "Asking the Open Notebook notebook chat",
    "tool_name": "opennotebook_chat",
    "tool_args": {
        "action": "ask",
        "notebook_id": "notebook-id-or-name",
        "message": "What endpoints does the API reference document?"
    }
}
~~~
