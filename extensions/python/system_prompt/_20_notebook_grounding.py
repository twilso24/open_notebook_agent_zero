"""Open Notebook Plugin - Automatic grounding from the chat context selection.

When the current chat has a Notebooks-chip selection stored on the server, this
hook loads the selected sources (existing insights first, else bounded full
text) and appends them to the system prompt, so the agent answers from the
notebook without calling a tool and without any notebook LLM call.

Grounding is cached per chat + selection digest so the HTTP work happens only
when the selection changes. Failures are swallowed: a broken backend must never
break the chat loop.
"""

import hashlib
import json

from helpers.extension import Extension
from agent import Agent, LoopData

from usr.plugins.open_notebook import config, client, telemetry
from usr.plugins.open_notebook.api.context_selection import read_selection
from usr.plugins.open_notebook.tools.context_selection import selection_to_context_config
from usr.plugins.open_notebook.tools.grounding import build_grounding

CACHE_KEY = "on_prompt_grounding_cache"
GROUNDING_BUDGET = 20000
MAX_NOTEBOOKS = 3


class NotebookGrounding(Extension):

    async def execute(
        self,
        system_prompt: list[str] = [],
        loop_data: LoopData = LoopData(),
        **kwargs,
    ):
        if not self.agent:
            return

        try:
            block = await self._build_block()
        except Exception:
            telemetry.set_unhealthy(True)
            return

        if block:
            system_prompt.append(block)

    async def _build_block(self) -> str:
        agent = self.agent
        ctx_id = (getattr(agent.context, "id", "") or "").strip()
        if not ctx_id:
            return ""

        selection = read_selection(ctx_id)
        if not isinstance(selection, dict):
            return ""
        if not selection:
            return ""

        digest = self._digest(selection)
        cache = agent.context.data.get(CACHE_KEY) or {}
        cached = cache.get("grounding") or {}
        if cached.get("digest") == digest and cached.get("text"):
            return cached["text"]

        api_url = config.get_api_url(agent)
        http_client = await client.get_client()

        parts: list[str] = []
        warnings: list[str] = []
        budget = GROUNDING_BUDGET

        for nb_id, nb_sel in list(selection.items())[:MAX_NOTEBOOKS]:
            if budget <= 0:
                warnings.append("notebook grounding budget reached; remaining notebooks skipped")
                break
            context_config = selection_to_context_config(nb_sel)
            resp = await http_client.post(
                f"{api_url}/api/chat/context",
                json={"notebook_id": nb_id, "context_config": context_config},
            )
            resp.raise_for_status()
            context = (resp.json() or {}).get("context") or {}
            sources = [s for s in (context.get("sources") or []) if isinstance(s, dict)]
            if not sources:
                continue
            text, meta = build_grounding(sources, budget=budget)
            if not text.strip():
                continue
            parts.append(f"### Notebook {nb_id}\n{text}")
            budget -= int(meta.get("total_chars") or 0)
            if meta.get("warning"):
                warnings.append(str(meta["warning"]))

        if not parts:
            return ""

        block = (
            "\n\n## OPEN NOTEBOOK CONTEXT (AUTO-GROUNDING)\n"
            "The user selected notebook context with the Notebooks chip. Answer questions "
            "about these notebooks from the text below and cite source titles. "
            "No notebook LLM was called. Use `opennotebook_chat:ask` only for extra content "
            "beyond this grounding.\n\n"
            + "\n\n".join(parts)
        )
        if warnings:
            block += "\n\nGrounding warnings: " + "; ".join(warnings)

        agent.context.data[CACHE_KEY] = {"grounding": {"digest": digest, "text": block}}
        return block

    @staticmethod
    def _digest(selection: dict) -> str:
        raw = json.dumps(selection, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
