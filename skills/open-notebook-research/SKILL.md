---
name: open-notebook-research
description: >
  Query and research your Open Notebook knowledge base with guided
  decision tree: search vs ask vs find. Includes iterative research
  strategy and model selection guidance.
version: 1.0.0
tags: ["research", "query", "search", "RAG", "ask", "knowledge", "find"]
triggers:
  - search knowledge base
  - ask notebook
  - research topic
  - find source
  - query notebook
  - RAG question
  - open notebook search
  - open notebook research
---

# Research & Knowledge Query — Decision Tree Skill

Query and research your Open Notebook knowledge base.
Use when the user wants to search, ask questions, or find specific content.

## Method Selection Decision Tree

```
User intent?
├── "Search for X" / "Find documents about X"
│   └── search (keyword or semantic)
├── "What is X?" / "Explain X" / "How does X work?"
│   └── ask (RAG with synthesized answer)
├── "Find the source named X" / "Where is X?"
│   └── find (exact name lookup)
├── "What relates to the concept of X"
│   └── search with search_type: vector
└── Unsure / exploratory
    └── search with search_type: text (broadest)
```

## Methods

### search — Keyword or Semantic Search

Returns ranked results with snippets and relevance scores.

~~~json
{
    "tool_name": "opennotebook_query",
    "tool_args": {
        "method": "search",
        "notebook_id": "optional-notebook-id",
        "query": "search terms",
        "search_type": "text"
    }
}
~~~

**Search types:**
- `text` (default) — keyword matching, fast, exact
- `vector` — semantic/conceptual matching, finds related ideas without exact keywords

### ask — RAG Question Answering

Synthesizes an answer from retrieved sources with citations.

~~~json
{
    "tool_name": "opennotebook_query",
    "tool_args": {
        "method": "ask",
        "notebook_id": "optional-notebook-id",
        "question": "natural language question",
        "model_name": "optional-model-hint"
    }
}
~~~

**Model selection cascade:**
1. Per-call `model_name` (fuzzy match: "deepseek", "gemini-2.5-flash", "openrouter")
2. Plugin setting `default_ask_model`
3. Auto-select (prefers OpenRouter/Ollama/DeepSeek over free Google models)

### find — Lookup by Name

Finds a specific source or note by name within a notebook. Uses fuzzy matching.

~~~json
{
    "tool_name": "opennotebook_query",
    "tool_args": {
        "method": "find",
        "notebook_id": "required-notebook-id",
        "name": "item name or partial name"
    }
}
~~~

## Iterative Research Strategy

When results are insufficient, follow this escalation path:

1. **search** (text) → broad keyword scan
2. **search** (vector) → conceptual/semantic expansion
3. **ask** → synthesized answer from all available sources
4. If still insufficient → suggest adding more sources with `opennotebook_sources:add`

## Cross-Tool Navigation

After getting results:
- Found an interesting source? → `opennotebook_sources:read` for full content
- Want to save a finding? → `opennotebook_notes:create` to capture it
- Want to explore a notebook? → `opennotebook_browse:notebook` for details

## Honest Boundaries

Always acknowledge when results are insufficient:
- "The knowledge base doesn't have enough information about X."
- Suggest adding more sources or refining the query.
- Never fabricate answers from thin air.
