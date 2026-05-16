### opennotebook_query:
search and query knowledge base

**Methods:** `search`, `ask`, `find`

**Key params:**
- `query` (string, for search) — keywords or phrase
- `search_type` ("text" or "vector", for search) — text=keyword, vector=semantic
- `question` (string, for ask) — natural language question
- `model_name` (string, optional for ask) — fuzzy match ("deepseek", "gemini-2.5-flash")
- `name` (string, for find) — item name to locate
- `notebook_id` (string) — scope to notebook (required for find)

💡 **Use the `open-notebook-research` skill for the full research workflow with decision tree and iterative strategy.**

usage:
~~~json
{
    "tool_name": "opennotebook_query",
    "tool_args": {
        "method": "search",
        "query": "search terms"
    }
}
~~~
