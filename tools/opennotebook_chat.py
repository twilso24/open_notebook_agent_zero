"""
Open Notebook Plugin - Chat Bridge Tool

Lets Agent Zero hold a grounded conversation with an Open Notebook notebook using
the notebook's own chat engine.

Methods:
    ask          — Send a message to a notebook chat; creates a session if needed.
    history      — Read the messages of an existing chat session.
    new_session  — Start a fresh chat session for a notebook.
    search       — Notebook-scoped content search.

Usage:
    Use `opennotebook_browse:notebooks` first to get a notebook ID or name.
    Then `opennotebook_chat:ask` with `notebook_id` and `message`.
"""

from helpers.tool import Tool, Response

from usr.plugins.open_notebook import config, client
from usr.plugins.open_notebook.shared import handle_error, resolve_notebook_id
from usr.plugins.open_notebook.api.context_selection import read_selection
from usr.plugins.open_notebook.tools.context_selection import selection_to_context_config
from usr.plugins.open_notebook.tools.grounding import build_grounding

# Hard cap on total grounding text per ask; over-budget sources are truncated with a warning.
GROUNDING_BUDGET = 20000


VALID_SOURCE_STATUS = {"insights", "full content", "not in"}
VALID_NOTE_STATUS = {"full content", "not in"}


class OpenNotebookChat(Tool):
    async def execute(self, **kwargs):
        method = (kwargs.get("action") or "ask").strip().lower()
        notebook = kwargs.get("notebook_id") or kwargs.get("notebook") or ""

        if method == "ask":
            return await self._ask(notebook, kwargs)
        if method == "history":
            return await self._history(kwargs.get("session_id") or "")
        if method == "new_session":
            return await self._new_session(notebook)
        if method == "search":
            return await self._search(notebook, kwargs.get("query") or kwargs.get("name") or "")

        return Response(
            message=(
                f"Unknown method '{method}'. Available: ask, history, new_session, search."
            ),
            break_loop=False,
        )

    # -- helpers ---------------------------------------------------------

    def _build_payload(self, context: dict) -> dict:
        """Shape the context response into the object /api/chat/execute expects.

        context must be a JSON object; sending a string returns HTTP 422.
        Disabled items are pruned: empty full_text and insights entries are dropped.
        """
        sources = []
        for src in context.get("sources") or []:
            if not isinstance(src, dict):
                continue
            item = {
                "id": src.get("id"),
                "title": src.get("title") or "",
                "full_text": src.get("full_text") or "",
                "insights": src.get("insights") or [],
            }
            if item["full_text"] or item["insights"]:
                sources.append(item)

        notes = []
        for note in context.get("notes") or []:
            if not isinstance(note, dict):
                continue
            item = {
                "id": note.get("id"),
                "title": note.get("title") or "",
                "content": note.get("content") or "",
            }
            if item["content"]:
                notes.append(item)

        return {"sources": sources, "notes": notes}

    @staticmethod
    def _sanitize_config(context_config) -> dict:
        """Validate a context_config map against the accepted statuses."""
        if not isinstance(context_config, dict):
            return {}
        clean = {}
        for section, allowed in (("sources", VALID_SOURCE_STATUS), ("notes", VALID_NOTE_STATUS)):
            mapping = context_config.get(section)
            if isinstance(mapping, dict):
                kept = {
                    str(k): str(v)
                    for k, v in mapping.items()
                    if str(v) in allowed
                }
                if kept:
                    clean[section] = kept
        return clean

    @staticmethod
    def _extract_answer(data: dict) -> str:
        messages = data.get("messages") or []
        for message in reversed(messages):
            if not isinstance(message, dict):
                continue
            if message.get("type") in ("human", "user"):
                continue
            content = message.get("content")
            if content:
                return str(content)
        return str(data.get("response") or data.get("message") or "")

    async def _create_session(self, http_client, api_url: str, notebook_id: str) -> str | None:
        resp = await http_client.post(
            f"{api_url}/api/chat/sessions", json={"notebook_id": notebook_id}
        )
        resp.raise_for_status()
        return (resp.json() or {}).get("id")

    # -- methods ---------------------------------------------------------

    async def _ask(self, notebook: str, kwargs: dict) -> Response:
        message = (kwargs.get("message") or kwargs.get("query") or "").strip()
        if not notebook:
            return Response(
                message="No notebook selected. Pick notebooks in the Notebooks context selector in the chat input before asking; I will not fall back to all sources.",
                break_loop=False,
            )
        if not message:
            return Response(message="Message required.", break_loop=False)

        try:
            notebook_id = await resolve_notebook_id(self.agent, notebook)
        except ValueError as e:
            return Response(message=f"**{e}**", break_loop=False)

        api_url = config.get_api_url(self.agent)
        http_client = await client.get_client()

        try:
            session_id = (kwargs.get("session_id") or "").strip()
            if not session_id:
                session_id = await self._create_session(http_client, api_url, notebook_id)
            if not session_id:
                return Response(
                    message="Failed to create a chat session for this notebook.",
                    break_loop=False,
                )

            ctx_id = getattr(getattr(self.agent, "context", None), "id", "") or ""
            stored = read_selection(ctx_id) if ctx_id else {}
            nb_selection = stored.get(notebook_id) if isinstance(stored, dict) else None
            if not kwargs.get("context_config") and isinstance(nb_selection, dict):
                context_config = selection_to_context_config(nb_selection)
            else:
                context_config = self._sanitize_config(kwargs.get("context_config"))
            context_resp = await http_client.post(
                f"{api_url}/api/chat/context",
                json={"notebook_id": notebook_id, "context_config": context_config},
            )
            context_resp.raise_for_status()
            context = (context_resp.json() or {}).get("context") or {}
            payload = self._build_payload(context)

            grounding, meta = build_grounding(payload["sources"], budget=GROUNDING_BUDGET)
            counts = (
                f"1 notebook, {len(meta['sources'])} sources grounded, {len(payload['notes'])} notes not yet included"
            )
            warn = f"\n\nWarning: {meta['warning']}" if meta["warning"] else ""
            return Response(
                message=(
                    "Grounding loaded from the notebook. No notebook LLM was called. "
                    "Answer the user's question from this text and cite source titles.\n\n"
                    f"{grounding}{warn}\n\n"
                    f"---\n session: `{session_id}` | context: {counts}"
                ),
                break_loop=False,
            )
        except Exception as e:
            return Response(
                message=handle_error(e, f"{api_url}/api/chat/context"),
                break_loop=False,
            )

    async def _history(self, session_id: str) -> Response:
        if not session_id:
            return Response(message="session_id required.", break_loop=False)
        api_url = config.get_api_url(self.agent)
        http_client = await client.get_client()
        try:
            resp = await http_client.get(f"{api_url}/api/chat/sessions/{session_id}")
            resp.raise_for_status()
            data = resp.json() or {}
            messages = data.get("messages") or []
            if not messages:
                return Response(message="Session has no messages.", break_loop=False)
            lines = []
            for m in messages:
                role = m.get("type") or "unknown"
                lines.append(f"**{role}**: {m.get('content') or ''}")
            return Response(
                message=f"Chat session `{session_id}`:\n\n" + "\n\n".join(lines),
                break_loop=False,
            )
        except Exception as e:
            return Response(
                message=handle_error(e, f"{api_url}/api/chat/sessions/{session_id}"),
                break_loop=False,
            )

    async def _new_session(self, notebook: str) -> Response:
        if not notebook:
            return Response(message="Notebook ID required.", break_loop=False)
        try:
            notebook_id = await resolve_notebook_id(self.agent, notebook)
        except ValueError as e:
            return Response(message=f"**{e}**", break_loop=False)

        api_url = config.get_api_url(self.agent)
        http_client = await client.get_client()
        try:
            session_id = await self._create_session(http_client, api_url, notebook_id)
            return Response(
                message=f"New chat session: `{session_id}` for `{notebook_id}`.",
                break_loop=False,
            )
        except Exception as e:
            return Response(
                message=handle_error(e, f"{api_url}/api/chat/sessions"),
                break_loop=False,
            )

    async def _search(self, notebook: str, query: str) -> Response:
        if not query:
            return Response(message="query required.", break_loop=False)

        notebook_id = ""
        if notebook:
            try:
                notebook_id = await resolve_notebook_id(self.agent, notebook)
            except ValueError as e:
                return Response(message=f"**{e}**", break_loop=False)

        api_url = config.get_api_url(self.agent)
        http_client = await client.get_client()
        try:
            params = {"query": query}
            if notebook_id:
                params["notebook_id"] = notebook_id
            resp = await http_client.get(f"{api_url}/api/search", params=params)
            resp.raise_for_status()
            data = resp.json()
            results = data.get("results") if isinstance(data, dict) else data
            results = results or []
            if not results:
                return Response(message=f"No results for '{query}'.", break_loop=False)
            lines = []
            for r in results[:20]:
                title = r.get("title") or r.get("name") or "Untitled"
                snippet = (r.get("content") or r.get("snippet") or "")
                snippet = snippet[:200].replace("\n", " ")
                lines.append(f"- **{title}** — {snippet}")
            return Response(
                message=f"Search results for '{query}':\n\n" + "\n".join(lines),
                break_loop=False,
            )
        except Exception as e:
            return Response(message=handle_error(e, f"{api_url}/api/search"), break_loop=False)
