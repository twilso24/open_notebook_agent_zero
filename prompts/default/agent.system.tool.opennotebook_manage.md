### opennotebook_manage:
manage Open Notebook plugin connection status, configuration, and notebook creation
usage:
~~~json
{
    "thoughts": [
        "Need to check Open Notebook connection...",
    ],
    "headline": "Checking Open Notebook status",
    "tool_name": "opennotebook_manage",
    "tool_args": {
        "method": "status"
    }
}
~~~

~~~json
{
    "thoughts": [
        "Need to create a notebook named test...",
    ],
    "headline": "Creating Open Notebook notebook",
    "tool_name": "opennotebook_manage",
    "tool_args": {
        "method": "create",
        "name": "test"
    }
}
~~~

**Methods:**

- `status` — Check if Open Notebook is reachable and healthy. Use when you need to verify connectivity or troubleshoot connection issues.
- `config` — Display current plugin configuration (API URL, read-only mode, confirmation settings). Use when the user wants to see or verify their settings.
- `create` — Create a new notebook. Use when the user asks to create, make, add, start, open, or name a notebook.

**Create parameters:**
- `name` (string, required) — Notebook name.
- `description` (string, optional) — Notebook description.
- Backend alias support for `title` and `notebook_name` is covered by `/a0/usr/plugins/open_notebook/tests/test_open_notebook_create_and_missing_notebook_regression.py`

**Natural language mapping:**
- "create a notebook named test" → `method: create`, `name: "test"`
- "make a notebook called test" → `method: create`, `name: "test"`
- "add notebook test" → `method: create`, `name: "test"`
- "open notebook test" → `method: create`, `name: "test"`
- "new notebook test" → `method: create`, `name: "test"`
- "create notebook named tester" → `method: create`, `name: "tester"`

**When to use:**
- User asks "is Open Notebook connected?" or "check connection" → use `status`
- User asks "what are my settings?" or "show configuration" → use `config`
- User asks to create, open, add, start, or name a notebook → use `create`
- Before performing any operation that requires Open Notebook connectivity → use `status` to verify
