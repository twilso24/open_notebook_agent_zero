### opennotebook_podcasts:
podcast episode generation and management

**Actions:** `profiles`, `list`, `get`, `generate`, `status`, `retry`, `delete`

**Key params:**
- `episode_profile` (string, required for generate) — profile **name** not ID
- `episode_name` (string, required for generate)
- `notebook_id` / `content` / `briefing_suffix` (optional for generate)
- `episode_id` (for get/retry/delete)
- `job_id` (for status)
- `confirmed` ("true"/"false")

⚠️ **This is an async workflow.** Use the `open_notebook-podcast` skill for the full guided workflow including polling strategy and timing estimates.

usage:
~~~json
{
    "tool_name": "opennotebook_podcasts",
    "tool_args": {
        "action": "generate",
        "episode_profile": "tech_discussion",
        "episode_name": "Episode Name",
        "notebook_id": "notebook-id"
    }
}
~~~
