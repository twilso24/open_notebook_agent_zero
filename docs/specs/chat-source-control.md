# Spec: Chat Source Control (revised, confirmed)

## Objective
Let the user choose exactly which sources, insights and notes a notebook chat can use. Controls live in the chat window, scoped to the current notebook. The chat window footer shows element counts, as in the reference screenshot.

## Domain Model
- Notebook: has sources and notes. Chat is scoped to one notebook.
- Source: holds full text. A source has zero or more insights (transformation outputs over its full text, e.g. Dense Summary).
- Note: user-authored text.

## Selection Model (confirmed)
- Each source is exactly one of: off, full text, or insights.
  - Insights mode lets the user enable each of that source's insights individually.
  - Full text and insights are never combined for the same source (Q2 answer A).
- A source with no insights cannot be set to insights mode.
- Each note is enabled or disabled independently.
- Example from the user: 10 insights in context = 7 insights from source A, 2 full text from source B, 1 disabled. Notes = 35 enabled, 2 disabled.

## Counting (confirmed)
- The footer counts context elements: enabled insights, and enabled notes. Full-text sources count as one element each.
- Token counts are the backend's responsibility. The app does not estimate tokens.

## User Stories
- As a user, I open the chat window and see the notebook's sources (each with its insights) and notes in a context panel.
- As a user, I set each source to off, full text, or insights, and toggle individual insights in insights mode.
- As a user, I toggle each note on or off.
- As a user, the footer shows the count of enabled insights and enabled notes.
- As a user, my selection is kept per notebook in browser storage and used for every chat message.

## Decisions
- Controls are in the chat window only. The bulk Chat context controls in the Sources and Notes tabs are removed.
- Selection persists per notebook in browser storage (localStorage key open_notebook:context:<notebook_id>).
- The app does not compute token counts.

## Backend Contract (verified)
- POST /api/chat/context accepts one status per source: 'not in' (off), 'insights', 'full content'. It cannot express individual insight selection.
- POST /api/chat/execute accepts context as a free-form dict (Pydantic Dict[str, Any]).
- The chat system prompt renders {{context}} as text. Graph state declares context as Optional[str].
- Source items returned by /api/chat/context include insights[] with insight_type and content.

## Backend Contract (confirmed live)
- POST /api/chat/execute requires context as a JSON object. A string is rejected with HTTP 422 ("Input should be a valid dictionary"). Verified live 2026-10-23.
- The app therefore sends a pruned context object: { sources: [...], notes: [...] }, matching the reference app. Full-mode sources carry full_text; insights-mode sources carry only enabled insights; included notes carry content. Disabled items are omitted.
- renderChatContextText remains as a helper mirroring backend formatting, but it is not sent to execute.

## Success Criteria
- An off source, disabled insight or disabled note is absent from the next chat request.
- A source in full text mode sends its full text and no insight text.
- A source in insights mode sends only its enabled insights.
- Footer counts match the enabled insights and enabled notes.
- Selections restore per notebook after reload and do not leak between notebooks.
- The podcast flow is unchanged.

## Commands
- Test: /opt/venv/bin/python -m pytest tests -v -p no:cacheprovider
- Syntax check: node --check webui/open_notebook-store.js

## Project Structure
- webui/open_notebook-store.js: selection state, persistence, context build, send path.
- webui/canvas-panel.html: chat-window context panel and footer counter. Remove bulk controls from the Sources and Notes tabs.
- webui/open_notebook.css and extensions/webui/page-head/open_notebook-head.html: styles, kept in sync.
- tests/: contract tests for store and markup.

## Boundaries
- Always: failing tests first; keep the podcast flow working; no credentials in localStorage.
- Ask first: backend API changes (Open Blocker b), new dependencies, commits or pushes.
- Never: send full text for a source set to insights; remove podcast selection behavior.

## Status
- Existing store logic reflects the older model (one status per source, with bulk controls). It must be revised to off/full/insights plus per-insight toggles.
- The bulk controls in canvas-panel.html must be removed.
