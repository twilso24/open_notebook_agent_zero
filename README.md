# 🎙️ Open Notebook Plugin for Agent Zero

> **Version: 0.2.1**

> **Browse notebooks, manage sources, take notes, find content by name, and generate AI podcast episodes — all from the Agent Zero sidebar.**

A knowledge management plugin that bridges [Open Notebook](https://github.com/lfnovo/open-notebook) into Agent Zero's WebUI, providing a full sidebar panel with notebook browsing, source management, notes CRUD, name-based fuzzy lookup, and async podcast generation.

---

## ✨ Features

### Notebooks
- Browse all notebooks with source/note counts and last-updated timestamps
- Hierarchical tree view for a bird's-eye overview
- Create notebooks from chat or sidebar — natural-language requests like `create a notebook named tester` and `open notebook tester` map to the create flow automatically
- Name-based fuzzy resolution (case-insensitive, emoji-stripped) across all tools
- Inline rename UI (no browser `prompt()` dialogs)

### Sources
- Import by **URL**, **raw text**, or **local file path**
- Auto-detection cascade: URL → File → Text
- Local files with known extensions (`.pdf`, `.doc`, `.docx`, `.txt`, `.md`, `.rtf`, `.odt`, `.epub`, `.html`, `.htm`, `.csv`) are automatically read and uploaded — no manual file handling needed
- Processing status with colored badges (`✅ completed`, `⏳ processing`, `❌ failed`)
- Source detail panel with metadata and full content viewer
- Delete sources from the panel

### Notes
- Full CRUD: list, create, read, update, delete
- Collaborative note creation — say "note this down" and the agent composes the note from conversation context
- Confirmation gates on destructive operations
- Inline editing — edit note title and content from the ⋮ menu in the Notes tab

### Name-Based Lookup
- Fuzzy search for sources and notes by name within a notebook
- Case-insensitive, partial-match support
- Returns unified results with type, name, ID, and status

### Podcast Generation
- Async multi-stage pipeline: outline → transcript → TTS audio
- Episode profile selection (format/style)
- Speaker config auto-injected from episode profile — no manual speaker selection needed
- Real-time pipeline-stage detection (sources loaded → outline → transcript → TTS)
- Episode management: list, get details, retry failed, delete
- Send transcript to Agent Zero chat
- Homepage generation with notebook selector dropdown; notebook tab shows episode list only

### Infrastructure
- **Reverse proxy** for remote access — frontend calls route through Agent Zero's API so remote clients can reach the Open Notebook backend without direct `localhost:5055` access
- **File upload bridge** — base64 multipart encoding allows file uploads through the proxy
- **Read-only mode** — optionally prevent all write/delete operations
- **Confirmation gates** — optionally require confirmation before destructive operations
- **Shared HTTP client** — lazy-singleton `httpx.AsyncClient` with connection pooling

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                    AGENT ZERO FRAMEWORK                          │
│                                                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐          │
│  │  browse   │  │  manage  │  │  notes   │  │  sources │          │
│  │ 🔍        │  │ ⚙️        │  │ 📝       │  │ 📚       │          │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘          │
│       └──────────────┴──────────────┴──────────────┘              │
│                          │                                       │
│                   ┌──────▼──────┐                                │
│                   │   query     │     ┌────────────┐             │
│                   │ 🤖 find     │     │  podcasts  │             │
│                   └──────┬──────┘     │ 🎙️ async   │             │
│                          │            └─────┬──────┘             │
│                          ▼                  ▼                     │
│              ┌──────────────────────────────────┐               │
│              │       REVERSE PROXY (api/)        │               │
│              │   JSON + binary + file uploads    │               │
│              └───────────────┬──────────────────┘               │
│                              │                                   │
└──────────────────────────────┼───────────────────────────────────┘
                               │
                    ┌──────────▼──────────┐
                    │   OPEN NOTEBOOK      │
                    │   host:5055          │
                    │   Notebooks · RAG    │
                    │   TTS · Embeddings   │
                    └─────────────────────┘
```

### Plugin Components

| Component | File(s) | Purpose |
|-----------|---------|---------|
| **Tools** (6) | `tools/opennotebook_*.py` | Agent-facing tools with method routing |
| **Reverse Proxy** | `api/proxy.py` | Bridges frontend ↔ Open Notebook backend |
| **HTTP Client** | `client.py` | Lazy-singleton `httpx.AsyncClient` with pooling |
| **Config** | `config.py`, `default_config.yaml` | Typed settings with env-var fallback |
| **Shared Helpers** | `shared.py`, `tools/shared.py` | Date/status formatting, name resolution, error translation |
| **Error Handler** | `errors.py` | HTTP/httpx exceptions → human-readable messages |
| **WebUI Store** | `webui/open_notebook-store.js` | Alpine.js reactive store (1,711 lines) |
| **Canvas Panel** | `webui/canvas-panel.html` | Sidebar UI template (646 lines) |
| **Styles** | `webui/open_notebook.css` | Panel styling |
| **Skills** (3) | `skills/` | Meta-skill, podcast workflow, research workflow |
| **Prompts** (6) | `prompts/default/` | Tool descriptions injected into agent context |
| **Setup** | `execute.py` | Connectivity check and dependency installer |

---

## 🔧 Installation

### Prerequisites

- [Agent Zero](https://github.com/frdel/AgentZero) running (Docker or local)
- [Open Notebook](https://github.com/lfnovo/open-notebook) backend running on port `5055`

### Steps

1. **Install the plugin** from the Agent Zero Plugins UI, or clone into your plugins directory:
   ```bash
   cd /a0/usr/plugins/
   git clone https://github.com/twilso24/open_notebook_agent_zero.git open_notebook
   ```

2. **Run setup** — click the setup button in Plugins UI, or run manually:
   ```bash
   python execute.py
   ```
   This checks backend connectivity and installs the `websockets` dependency if needed.

3. **Verify connection** — in the Agent Zero chat:
   ```json
   {
       "tool_name": "opennotebook_manage",
       "tool_args": { "method": "status" }
   }
   ```

### Configuration

Settings are managed via the Plugins UI or `default_config.yaml`:

| Setting | Default | Description |
|---------|---------|-------------|
| `api_url` | `http://host.docker.internal:5055` | Open Notebook backend URL (Docker Desktop) |
| `read_only` | `false` | Prevents all write/delete operations |
| `confirmations` | `true` | Requires confirmation before destructive operations |

Environment variable `OPEN_NOTEBOOK_API_URL` overrides `api_url` if set.

> **Non-Docker setups:** Set `api_url` to `http://localhost:5055` if Agent Zero and Open Notebook run on the same host.

---

## 🛠️ Tools Reference

| Tool | Methods | Description |
|------|---------|-------------|
| `opennotebook_browse` | `notebooks`, `notebook`, `tree` | Explore notebooks, inspect details, hierarchical overview |
| `opennotebook_manage` | `status`, `config`, `create` | Check connectivity, view settings, create notebooks |
| `opennotebook_sources` | `list`, `add`, `read`, `delete` | Manage content sources with auto-type detection |
| `opennotebook_notes` | `list`, `create`, `read`, `update`, `delete` | Full CRUD for notebook notes |
| `opennotebook_query` | `find` | Name-based fuzzy lookup for sources and notes |
| `opennotebook_podcasts` | `profiles`, `list`, `get`, `generate`, `status`, `retry`, `delete` | Async podcast episode generation and management |

### Skills

| Skill | Trigger | Purpose |
|-------|---------|---------|
| `open_notebook` | "open notebook", "knowledge base", "notebooks" | Meta-skill: tool map, user journeys, setup guidance |
| `open_notebook-podcast` | "create podcast", "podcast generation" | Full async workflow with polling strategy and timing |
| `open_notebook-research` | "find source", "research topic", "look up" | Name-based lookup workflow with cross-tool navigation |

---

## 📋 Usage Examples

### Browse Notebooks
```json
{
    "tool_name": "opennotebook_browse",
    "tool_args": { "method": "notebooks" }
}
```

### Add a Source (URL)
```json
{
    "tool_name": "opennotebook_sources",
    "tool_args": {
        "method": "add",
        "notebook_id": "notebook:uiv698qm1c0kkbfpdp4u",
        "content": "https://example.com/article"
    }
}
```

### Add a Source (Local File)
```json
{
    "tool_name": "opennotebook_sources",
    "tool_args": {
        "method": "add",
        "notebook_id": "notebook:uiv698qm1c0kkbfpdp4u",
        "content": "/path/to/report.pdf"
    }
}
```
The file is automatically detected, read, and uploaded — no manual processing needed.

### Create a Note
```json
{
    "tool_name": "opennotebook_notes",
    "tool_args": {
        "method": "create",
        "notebook_id": "notebook:uiv698qm1c0kkbfpdp4u",
        "title": "Key Findings",
        "content": "The clarity optimization improved average scores by 18.7 points."
    }
}
```

### Find an Item by Name
```json
{
    "tool_name": "opennotebook_query",
    "tool_args": {
        "method": "find",
        "notebook_id": "notebook:uiv698qm1c0kkbfpdp4u",
        "name": "clarity"
    }
}
```

### Generate a Podcast
```json
{
    "tool_name": "opennotebook_podcasts",
    "tool_args": {
        "method": "generate",
        "episode_profile": "tech_discussion",
        "episode_name": "Deep Dive: Clarity Optimization",
        "notebook_id": "notebook:uiv698qm1c0kkbfpdp4u"
    }
}
```
Returns a `job_id` — wait 3–5 minutes, then check status:
```json
{
    "tool_name": "opennotebook_podcasts",
    "tool_args": { "method": "status", "job_id": "returned-job-id" }
}
```

---

## 🎙️ Podcast Pipeline

Podcast generation is a **multi-stage async workflow**:

```
Sources → Outline → Transcript → TTS Audio → Episode
```

| Stage | Typical Duration |
|-------|----------------|
| Outline generation | 2–5 min |
| Transcript generation | 3–8 min |
| TTS audio rendering | 5–15 min |
| **Total** | **10–25 min** |

**Speaker configuration** is automatically fetched from the selected episode profile's `speaker_config` — the proxy injects it transparently for backend compatibility. No separate speaker selection is needed from the plugin.

---

## 📐 Design Principles

- **Action guidance** — every tool response tells the user what to do next
- **Cross-tool navigation** — messages reference related tools (e.g., "Use `opennotebook_browse:notebooks` to see all notebooks")
- **Inline comments** — every method has docstrings explaining purpose and behavior
- **Error recovery** — HTTP exceptions are translated into human-readable messages with suggested fixes
- **Confirmation gates** — destructive operations require explicit confirmation when enabled

---

## 🔄 Changelog

Key milestones from the commit history:

| Commit | Description |
|--------|-------------|
| `933d062` | Feature: inline note editing UI for existing notes (version 0.2.1) |
| `e8c425b` | Fix rename notebook/session: replace `prompt()` with inline UI |
| `185b408` | Proxy auto-inject: dynamically fetch `speaker_config` from episode profile for backend compatibility |
| `a2c8cc0` | Remove `speaker_profile` from podcast generation — only pass episode name, profile, content, and instructions |
| `81ad72e` | Refactor: remove generation features from Podcasts tab (episodes list only) |
| `4e85c61` | Fix: restore homepage podcast with notebook selector dropdown |
| `6929366` | Feature: notebook-scoped podcast generation with source content mode toggle |
| `9707af9` | Feature: source detail panel with metadata and content viewer |
| `b006908` | Fix: enable file uploads through base64 multipart proxy bridge |
| `0bce212` | Feature: notebook list refresh button |
| `9941298` | Major plugin overhaul: fix CRUD workflow, remove beta features, fix UI |
| `845379b` | Fix: resolve 6 bugs in sources and query tools |

---

## 📁 Project Structure

```
open_notebook/
├── plugin.yaml              # Plugin manifest
├── config.py                # Settings access (api_url, read_only, confirmations)
├── default_config.yaml      # Default configuration values
├── client.py                # Shared httpx.AsyncClient singleton
├── shared.py                # Formatting, name resolution, error routing
├── errors.py                # HTTP/httpx exception translator
├── execute.py               # Setup script (connectivity + deps)
├── requirements.txt         # httpx>=0.24.0
├── LICENSE                  # MIT
│
├── api/
│   └── proxy.py             # Reverse proxy (JSON + binary + uploads)
│
├── tools/
│   ├── opennotebook_browse.py     # Notebook discovery (272 lines)
│   ├── opennotebook_manage.py     # Status, config, create (215 lines)
│   ├── opennotebook_sources.py    # Source management (785 lines)
│   ├── opennotebook_notes.py      # Notes CRUD (536 lines)
│   ├── opennotebook_query.py      # Name-based lookup (174 lines)
│   ├── opennotebook_podcasts.py   # Podcast generation (654 lines)
│   └── shared.py                  # Tool-level shared helpers (146 lines)
│
├── prompts/default/               # Agent tool descriptions (6 files)
│
├── skills/
│   ├── open_notebook/SKILL.md           # Meta-skill
│   ├── open_notebook-podcast/SKILL.md   # Async podcast workflow
│   └── open_notebook-research/SKILL.md  # Name-based lookup workflow
│
├── webui/
│   ├── open_notebook-store.js      # Alpine.js store (1,674 lines)
│   ├── canvas-panel.html           # Sidebar UI template (622 lines)
│   ├── open_notebook.css           # Panel styles
│   └── thumbnail.jpg              # Plugin thumbnail
│
└── extensions/
    ├── python/                    # Backend lifecycle hooks
    └── webui/                     # Frontend lifecycle hooks
```

---

## 📄 License

MIT — see [LICENSE](LICENSE)

---

*Built for [Agent Zero](https://github.com/frdel/AgentZero) • Powered by [Open Notebook](https://github.com/lfnovo/open-notebook)*
