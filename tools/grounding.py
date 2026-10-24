"""Build a bounded grounding block from notebook sources.

No LLM calls: insights are preferred when present, otherwise full text is
capped per source (header included). A hard total budget truncates and warns.
"""

FULL_TEXT_CAP = 8000


def build_grounding(sources, budget=50000):
    parts = []
    meta_sources = []
    total = 0
    warning = ""

    for src in sources:
        title = src.get("title") or src.get("id") or "untitled"
        header = f"## {title}\n"
        insights = [str(i).strip() for i in (src.get("insights") or []) if str(i).strip()]
        if insights:
            mode = "insights"
            block = header + "\n".join(insights)
        else:
            mode = "full"
            block = header + (src.get("full_text") or "")[: FULL_TEXT_CAP - len(header)]
        block = block[:FULL_TEXT_CAP]
        if not block[len(header):].strip():
            continue

        room = budget - total
        if room <= 0:
            warning = f"grounding budget of {budget} chars reached; remaining sources skipped"
            break
        if len(block) > room:
            block = block[:room]
            warning = f"grounding budget of {budget} chars reached; '{title}' truncated"
            parts.append(block)
            total += len(block)
            meta_sources.append({"id": src.get("id"), "mode": mode, "chars": len(block)})
            break

        parts.append(block)
        total += len(block)
        meta_sources.append({"id": src.get("id"), "mode": mode, "chars": len(block)})

    text = "\n\n".join(parts)
    return text, {"sources": meta_sources, "total_chars": total, "warning": warning}
