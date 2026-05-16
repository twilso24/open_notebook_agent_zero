"""
Open Notebook Plugin - Query Tool

Provides knowledge retrieval and search capabilities across Open Notebook sources.
Querying searches through processed sources and notes that have been embedded into
the notebook's vector store.

Methods:
    search — Keyword or semantic search across sources and notes in a notebook.
             Returns ranked results with relevance scores and content snippets.
    ask    — Ask a natural language question using RAG (Retrieval-Augmented Generation).            Combines source retrieval with LLM-powered answer synthesis.
    find   — Look up a specific source or note by name within a notebook.
             Uses fuzzy name matching for flexible lookups.

Usage:
    First add sources via `opennotebook_sources:add`, then use `search` or `ask`
    to query your knowledge base. Use `find` when you know the name of an item.
"""

from helpers.tool import Tool, Response

import sys
from pathlib import Path

# Add plugin root to path for shared imports (config, client, errors)
_plugin_root = str(Path(__file__).resolve().parent.parent)
if _plugin_root not in sys.path:
    sys.path.insert(0, _plugin_root)

try:
    import httpx
except ImportError:
    httpx = None
import config
import client
import errors
from shared import format_date, format_status, get_asset_type, handle_error

# Limits for display — prevents overwhelming output
_MAX_RESULTS = 10
_MAX_SNIPPET_CHARS = 200  # Truncate long snippets for table readability

class OpenNotebookQuery(Tool):
    async def execute(self, **kwargs):
        """Route to the correct query method based on self.method.

        Supported methods: search, ask, find.
        Defaults to 'search' if no method is specified.

        Returns:
            Response: The result from the delegated method handler.
        """
        method = self.method or "search"

        if method == "search":
            # Search sources and notes by keyword or vector similarity
            notebook_id = kwargs.get("notebook_id", "")
            query = kwargs.get("query", "")
            search_type = kwargs.get("search_type", "text")
            return await self._search(notebook_id, query, search_type)
        elif method == "ask":
            # RAG-powered question answering over notebook content
            notebook_id = kwargs.get("notebook_id", "")
            question = kwargs.get("question", "")
            model_name = kwargs.get("model_name", "")
            return await self._ask(notebook_id, question, model_name)
        elif method == "find":
            # Find a specific source or note by name
            notebook_id = kwargs.get("notebook_id", "")
            name = kwargs.get("name", "")
            return await self._find(notebook_id, name)
        else:
            return Response(
                message=(
                    f"❌ **Unknown method '{method}'.**\n"
                    f"Available methods: `search`, `ask`, `find`.\n"
                    "Use `opennotebook_query:search` with a `query` to start searching."
                ),
                break_loop=False,
            )

    async def _search(self, notebook_id: str, query: str, search_type: str) -> Response:
        """Search sources and notes with keyword or semantic (vector) search.

        Args:
            notebook_id: Optional notebook to scope the search to.
            query: The search keywords or natural language phrase.
            search_type: 'text' for keyword matching, 'vector' for semantic search.

        Returns:
            Response: A markdown table of ranked results with source name, snippet,
                      and relevance score, or an empty-state message with suggestions.
        """
        # Validate required query parameter
        if not query:
            return Response(
                message=(
                    "❌ **Search query required.**\n"
                    "Provide keywords or a search phrase. "
                    "Use `opennotebook_sources:list` to check available sources first."
                ),
                break_loop=False,
            )

        # Normalize search type — only 'text' and 'vector' are valid
        if search_type not in ("text", "vector"):
            search_type = "text"

        # Build API request — POST /api/search with combined source+note search
        api_url = config.get_api_url(self.agent)
        url = f"{api_url}/api/search"

        body = {
            "query": query,
            "type": search_type,
            "limit": _MAX_RESULTS + 1,  # Request one extra to detect overflow
            "search_sources": True,
            "search_notes": True,
        }

        try:
            http_client = await client.get_client()
            response = await http_client.post(url, json=body)
            response.raise_for_status()
            data = response.json()

            # Extract results and metadata from API response
            results = data.get("results", [])
            total_count = data.get("total_count", 0)
            actual_type = data.get("search_type", search_type)

            # Handle empty results — suggest adding more sources or different keywords
            if not results:
                return Response(
                    message=(
                        f"🔍 **No results found for '{query}'.**\n"
                        "Try different keywords, or use `opennotebook_sources:list` to check "
                        "if sources have been added and processed."
                    ),
                    break_loop=False,
                )

            # Build markdown results table with ranked results
            lines = [f"🔍 **Search Results** (`{actual_type}` search)\n"]
            lines.append("| # | Source | Snippet | Score |")
            lines.append("|---|--------|---------|-------|")

            for i, result in enumerate(results[:_MAX_RESULTS], 1):
                # Extract source name from various possible field names
                source_name = result.get("source_title", "") or result.get("title", "") or result.get("name", "Unknown")
                # Extract content snippet from various possible field names
                snippet = result.get("content", "") or result.get("text", "") or result.get("snippet", "")
                # Truncate long snippets for table readability
                if len(snippet) > _MAX_SNIPPET_CHARS:
                    snippet = snippet[:_MAX_SNIPPET_CHARS] + "..."
                score = result.get("score", "")
                score_str = f"{score:.2f}" if isinstance(score, (int, float)) else str(score)
                lines.append(f"| {i} | **{source_name}** | {snippet} | {score_str} |")

            # Indicate truncation when there are more results than displayed
            if total_count > _MAX_RESULTS:
                remaining = total_count - _MAX_RESULTS
                lines.append(
                    f"\n...and {remaining} more results. "
                    f"Refine your search query or use `opennotebook_query:ask` for a focused answer."
                )

            # Show notebook scope if provided
            if notebook_id:
                lines.insert(1, f"*Notebook: `{notebook_id}`*\n")

            return Response(
                message="\n".join(lines),
                break_loop=False,
            )

        except Exception as e:
            return Response(message=handle_error(e, url), break_loop=False)

    async def _ask(self, notebook_id: str, question: str, model_name: str = "") -> Response:
        """Ask a natural language question using RAG (Retrieval-Augmented Generation).

        Sends a question to the Open Notebook API which retrieves relevant sources
        and uses an LLM to synthesize a grounded answer.

        Args:
            notebook_id: Optional notebook to scope the answer to.
            question: The natural language question to answer.
            model_name: Optional model hint (partial name or provider) for answer generation.

        Returns:
            Response: An AI-generated answer grounded in notebook sources, or an
                      error/insufficient-context message with suggestions.
        """
        # Validate required question parameter
        if not question:
            return Response(
                message=(
                    "❌ **Question required.**\n"
                    "Provide a natural language question. "
                    "Use `opennotebook_query:search` for keyword-based lookups instead."
                ),
                break_loop=False,
            )

        # Build API request — POST /api/search/ask/simple with resolved models
        api_url = config.get_api_url(self.agent)
        url = f"{api_url}/api/search/ask/simple"

        # Resolve model: per-call override > plugin default > auto-select
        default_model = config.get_default_ask_model(self.agent)
        hint = model_name or default_model
        models = await self._resolve_model(api_url, hint)

        body = {
            "question": question,
            "strategy_model": models["strategy"],
            "answer_model": models["answer"],
            "final_answer_model": models["final"],
        }

        try:
            # Use extended timeout — RAG answer generation can take 30-120 seconds
            http_client = await client.get_client()

            # Try SSE stream first, fall back to JSON
            strategy = ""
            answer_parts = []
            final_answer = ""
            json_data = None

            try:
                async with http_client.stream(
                    "POST", url, json=body, timeout=httpx.Timeout(15.0, read=120.0)
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line.startswith("data: "):
                            continue
                        try:
                            import json as _json
                            payload = _json.loads(line[6:])
                        except Exception:
                            continue
                        event_type = payload.get("type", "")
                        if event_type == "strategy":
                            strategy = payload.get("content", "")
                        elif event_type == "answer":
                            content = payload.get("content", "")
                            if content:
                                answer_parts.append(content)
                        elif event_type == "final_answer":
                            final_answer = payload.get("content", "")
            except Exception:
                # Fallback: try standard JSON response
                resp = await http_client.post(url, json=body, timeout=httpx.Timeout(15.0, read=120.0))
                resp.raise_for_status()
                json_data = resp.json()
                final_answer = json_data.get("answer", "")

            # Use final_answer if available, otherwise join answer parts
            answer = final_answer or "".join(answer_parts)

            # Check for insufficient context
            if not answer or answer.strip().lower() in ("null", "none", "", "insufficient"):
                return Response(
                    message=(
                        "💡 **I couldn't find enough information to answer this question.**\n"
                        "Consider adding more relevant sources with `opennotebook_sources:add`, "
                        "or use `opennotebook_query:search` to explore what content is available."
                    ),
                    break_loop=False,
                )

            # Build answer display with optional model and notebook context
            lines = [f"💡 **Answer**\n"]
            if models.get("display_name"):
                lines.insert(1, f"*Model: {models['display_name']}*\n")
            if notebook_id:
                lines.insert(1, f"*Notebook: `{notebook_id}`*\n")
            lines.append(answer)

            return Response(
                message="\n".join(lines),
                break_loop=False,
            )

        except httpx.TimeoutException:
            return Response(
                message=(
                    "⚠️ **Timeout** — the question may be too broad for the available sources.\n"
                    "Try a more specific question, or use `opennotebook_query:search` for faster results."
                ),
                break_loop=False,
            )
        except Exception as e:
            return Response(message=handle_error(e, url), break_loop=False)

    async def _find(self, notebook_id: str, name: str) -> Response:
        """Find a specific source or note by name within a notebook.

        Uses case-insensitive fuzzy matching — the search term can be a substring
        of the actual name, or vice versa.

        Args:
            notebook_id: The notebook to search within (required — find is notebook-scoped).
            name: The name or identifier to search for.

        Returns:
            Response: A table of matching items with type, name, ID, and status,
                      or a not-found message with alternative search suggestions.
        """
        if not notebook_id:
            return Response(
                message=(
                    "❌ **Notebook ID required.** Find is notebook-scoped.\n"
                    "Use `opennotebook_browse:notebooks` to list all notebooks and their IDs, "
                    "then pass the ID here to search within a specific notebook."
                ),
                break_loop=False,
            )

        # Validate required name parameter
        if not name:
            return Response(
                message=(
                    "❌ **Name required.**\n"
                    "Provide the name or partial name to search for. "
                    "Use `opennotebook_sources:list` to browse all sources in the notebook."
                ),
                break_loop=False,
            )

        # Fetch all sources in this notebook for local fuzzy matching
        api_url = config.get_api_url(self.agent)

        try:
            http_client = await client.get_client()

            # Search sources in this notebook — GET /api/sources filtered by notebook
            sources_url = f"{api_url}/api/sources"
            source_response = await http_client.get(
                sources_url, params={"notebook_id": notebook_id, "limit": 100}
            )
            source_response.raise_for_status()
            sources = source_response.json()

            # Filter by name similarity — case-insensitive substring matching
            name_lower = name.lower()
            matches = []
            for src in sources:
                title = (src.get("title") or "").lower()
                # Bidirectional substring match for flexibility
                if name_lower in title or title in name_lower:
                    matches.append({
                        "type": "source",
                        "name": src.get("title") or "Untitled",
                        "id": src.get("id", ""),
                        "status": src.get("status", ""),
                    })

            # Handle no matches — suggest broader search alternatives
            if not matches:
                return Response(
                    message=(
                        f"🔍 **No item found matching '{name}' in this notebook.**\n"
                        "Try a different name, or use `opennotebook_query:search` for broader keyword search."
                    ),
                    break_loop=False,
                )

            # Build results table with matched items
            lines = [f"🔍 **Found {len(matches)} match(es)**\n"]
            lines.append("| Type | Name | ID | Status |")
            lines.append("|------|------|----|--------|")

            for m in matches:
                status = m.get("status", "") or "completed"
                lines.append(f"| {m['type']} | **{m['name']}** | `{m['id']}` | {status} |")

            return Response(
                message="\n".join(lines),
                break_loop=False,
            )

        except Exception as e:
            return Response(message=handle_error(e, f"{api_url}/api/sources"), break_loop=False)

    async def _resolve_model(self, api_url: str, model_hint: str = "") -> dict:
        """Resolve model IDs with fuzzy matching and smart fallback.

        Attempts to find the best matching language model through a cascade:
        1. Exact name match (case-insensitive)
        2. Fuzzy substring match (hint ⊂ name or name ⊂ hint)
        3. Provider prefix match (e.g. 'deepseek' matches provider field)
        4. Auto-select from preferred providers (openrouter → openai_compatible → ollama → deepseek)
        5. Final fallback: first available language model

        Args:
            api_url: The base API URL for fetching available models.
            model_hint: Optional partial model name or provider for matching.

        Returns:
            dict with keys: strategy, answer, final (model IDs), display_name (human-readable).
            Returns empty strings if no models are available.
        """
        try:
            http_client = await client.get_client()
            # Fetch all available models — GET /api/models
            response = await http_client.get(f"{api_url}/api/models")
            if response.status_code != 200:
                return {"strategy": "", "answer": "", "final": "", "display_name": ""}

            data = response.json()
            if not isinstance(data, list) or not data:
                return {"strategy": "", "answer": "", "final": "", "display_name": ""}

            # Filter to language models only (exclude embedding, image, etc.)
            lang_models = [m for m in data if isinstance(m, dict) and m.get("type") == "language"]
            if not lang_models:
                return {"strategy": "", "answer": "", "final": "", "display_name": ""}

            chosen = None

            if model_hint:
                hint_lower = model_hint.lower().strip()

                # Step 1: Exact name match (case-insensitive)
                for m in lang_models:
                    if m.get("name", "").lower() == hint_lower:
                        chosen = m
                        break

                # Step 2: Fuzzy — hint is a substring of model name (or vice versa)
                if not chosen:
                    for m in lang_models:
                        name = m.get("name", "").lower()
                        if hint_lower in name or name in hint_lower:
                            chosen = m
                            break

                # Step 3: Provider prefix match (e.g. 'deepseek' → provider field)
                if not chosen:
                    for m in lang_models:
                        provider = m.get("provider", "").lower()
                        if hint_lower in provider or provider in hint_lower:
                            chosen = m
                            break

            # Step 4: Auto-select from preferred providers (better rate limits / quality)
            if not chosen:
                preferred = ["openrouter", "openai_compatible", "ollama", "deepseek"]
                for pref in preferred:
                    for m in lang_models:
                        if pref in m.get("provider", "").lower():
                            chosen = m
                            break
                    if chosen:
                        break

            # Step 5: Final fallback — first available language model
            if not chosen:
                chosen = lang_models[0]

            # Return model IDs for all three RAG pipeline stages
            model_id = chosen.get("id", "")
            display_name = chosen.get("name", model_id)
            return {
                "strategy": model_id,
                "answer": model_id,
                "final": model_id,
                "display_name": display_name,
            }

        except Exception:
            # Graceful fallback — empty strings let the API use its own defaults
            return {"strategy": "", "answer": "", "final": "", "display_name": ""}

