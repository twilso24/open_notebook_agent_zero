"""Open Notebook plugin: per-chat context selection mirror.

Stores the Agent Zero chat context selector state (per notebook: sources,
insights, notes) so the opennotebook_chat tool can read it server-side.

GET  /api/plugins/open_notebook/context_selection?context_id=...
POST /api/plugins/open_notebook/context_selection  {context_id, selection}
"""

import json
import re
from pathlib import Path

from helpers.api import ApiHandler, Request, Response

DATA_DIR = Path("/a0/usr/plugins/open_notebook/data/selections")


def _safe_context_id(value) -> str:
    return re.sub(r"[^A-Za-z0-9_-]", "", str(value or ""))[:64]


def _path_for(context_id: str) -> Path:
    return DATA_DIR / f"{context_id}.json"


def read_selection(context_id: str) -> dict:
    """Return the stored selection for a chat context, or an empty dict."""
    safe = _safe_context_id(context_id)
    if not safe:
        return {}
    path = _path_for(safe)
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text())
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


class ContextSelectionHandler(ApiHandler):
    @classmethod
    def get_methods(cls) -> list[str]:
        return ["GET", "POST"]

    async def process(self, input: dict, request: Request) -> dict | Response:
        if request.method == "GET":
            context_id = request.args.get("context_id", "")
            safe = _safe_context_id(context_id)
            if not safe:
                return {"success": False, "error": "context_id required"}
            return {"success": True, "context_id": safe, "selection": read_selection(safe)}

        context_id = _safe_context_id(input.get("context_id"))
        if not context_id:
            return {"success": False, "error": "context_id required"}
        selection = input.get("selection")
        if not isinstance(selection, dict):
            return {"success": False, "error": "selection must be an object"}

        DATA_DIR.mkdir(parents=True, exist_ok=True)
        _path_for(context_id).write_text(json.dumps(selection, ensure_ascii=False))
        return {"success": True, "context_id": context_id}
