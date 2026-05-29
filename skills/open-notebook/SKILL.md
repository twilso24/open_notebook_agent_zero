---
name: open-notebook
description: >
  Open Notebook plugin meta-skill. Provides tool map, user journeys,
  first-time setup guidance, and cross-tool orchestration for the
  Open Notebook personal knowledge management plugin.
version: 1.0.0
tags: ["open-notebook", "plugin", "knowledge", "management", "orchestration"]
triggers:
  - open notebook
  - knowledge base
  - notebooks
  - sources
  - what notebooks do I have
  - show my knowledge
---

# Open Notebook — Plugin Meta-Skill

Open Notebook personal knowledge management plugin for Agent Zero.
Provides AI-powered notebooks, source management, name-based lookup, and podcast generation.

Use when the user mentions Open Notebook, knowledge base, notebooks, sources, or podcasts.

## Available Tools

| Tool | Purpose | Key Methods |
|------|---------|-------------|
| `opennotebook_browse` | Explore notebooks | `notebooks`, `notebook`, `tree` |
| `opennotebook_manage` | Connection status & config | `status`, `config` |
| `opennotebook_sources` | Manage content sources | `list`, `add`, `read`, `delete` |
| `opennotebook_notes` | Manage notes | `list`, `create`, `read`, `update`, `delete` |
| `opennotebook_query` | Name-based lookup | `find` |
| `opennotebook_podcasts` | Podcast generation | `profiles`, `generate`, `status`, `list`, `get`, `retry`, `delete` |

## User Journey Maps

### Explore Knowledge Base
1. `opennotebook_browse:notebooks` → see all notebooks
2. `opennotebook_browse:notebook` → inspect a specific notebook
3. `opennotebook_sources:list` → see sources in that notebook
4. `opennotebook_query:find` → look up specific items by name

### Research a Topic
1. Use the **open-notebook-research** skill for guided query workflow
2. `opennotebook_query:find` → locate specific items by name
3. `opennotebook_notes:create` → save findings as a note

### Add Content
1. `opennotebook_browse:notebooks` → pick a notebook
2. `opennotebook_sources:add` → add URL, file, or text
3. Wait for processing (check with `opennotebook_sources:list`)
4. `opennotebook_sources:list` → verify content was added

### Create a Podcast
1. Use the **open-notebook-podcast** skill for the full async workflow
2. `opennotebook_podcasts:profiles` → pick profiles
3. `opennotebook_podcasts:generate` → start generation (returns job_id)
4. Wait 3-5 min → `opennotebook_podcasts:status` → check progress
5. Repeat until complete → `opennotebook_podcasts:get` → retrieve episode

## First-Time Setup

1. `opennotebook_manage:status` → verify connection to port 5055
2. `opennotebook_browse:notebooks` → see existing notebooks
3. If empty → guide user to create a notebook and add sources

## Plugin Configuration

Use `opennotebook_manage:config` to view settings:
- **API URL** — Open Notebook backend address
- **Read Only** — prevents write/delete operations
- **Confirmations** — requires confirmation before destructive ops

## Prerequisites

- Open Notebook backend running on port 5055
- Plugin enabled in Agent Zero
