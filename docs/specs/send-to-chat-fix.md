# Spec: Fix Send-to-A0-Chat for Notes and Chat Replies

## Objective
The 'to A0 Chat' action on notes (canvas-panel.html ~518) and on chat replies (~618) does not place text in the Agent Zero chat composer. Sources and podcasts work. Make all four entry points (source, note, podcast, chat reply) reliably insert their content into the composer.
Success: clicking '→ A0 Chat' on a note or chat reply of any length leaves that content in the #chat-input composer, ready to send, with no data loss.

## Root Cause (verified by code review)
1. open_notebook-store.js sendToChat() reads Alpine.store('inputStore'). The core composer store is registered as createStore('chatInput') in webui/components/chat/input/input-store.js:776. The lookup returns undefined, so the store branch is dead code.
2. The DOM fallback sets chatInput.value on #chat-input. That element is a contenteditable div, so .value has no effect on its text.
3. The fallback then dispatches an 'input' event. That calls chatInput.handleInput, which runs _syncMessageFromEditor and overwrites _message with the empty editor text. The content is lost.
4. Long content (> 2000 chars) goes through _sendAsFile, which uses the real chatAttachments store, so it works. Short notes and replies take the broken direct path. This explains the symptom.

## Commands
Plugin source: /a0/usr/plugins/open_notebook (symlink to git repo)
Syntax check: node --check webui/open_notebook-store.js
Backend tests: pytest tests/ -q
Manual verify: hard-refresh the Agent Zero WebUI, then click '→ A0 Chat' on a short note.

## Project Structure
webui/open_notebook-store.js  -> sendToChat, _sendAsFile, send* wrappers (edit here)
webui/canvas-panel.html     -> entry-point buttons (no change expected)
tests/                      -> add regression tests if a JS test harness exists, else document manual test

## Code Style
Keep the existing store style (2/4-space mix as present, single quotes, async/await). Use the core store via Alpine.store('chatInput') and its message setter. Do not touch DOM .value on the composer.

Example:
const composer = Alpine.store('chatInput');
if (composer) composer.message = msg;

## Required Fix
A. sendToChat(text, sources): replace the inputStore lookup with Alpine.store('chatInput'). Set its message property (the setter re-renders the contenteditable). Remove chatInput.value and the synthetic input event.
B. After setting the message, focus #chat-input and move the caret to the end using the store's existing _setEditorCaret or an equivalent Range call.
C. Consider reusing the append helper in webui/index.js (around line 232-241) so the inserted text is appended to an existing draft rather than replacing it. Decide with the user (see Open Questions).
D. _sendAsFile fallback: apply the same store-based update for the 'Review the attached file:' prompt. Keep the chatAttachments.addAttachment path unchanged.
E. Guard: if the chatInput store is missing, show a toast error instead of failing silently.

## Testing Strategy
- Manual matrix (must all pass): short note, long note (>2000 chars), short chat reply, long chat reply, source, podcast episode.
- For each: content appears in composer text, nothing is lost after an extra keystroke, Enter sends the full text, and the toast shows.
- Edge cases: empty composer, non-empty draft, composer with a code block, no chat selected.
- Verify with a browser run (browser-automation skill) and a screenshot after each click.

## Boundaries
- Always: keep sources/podcasts behavior unchanged; verify all six matrix cases before commit.
- Ask first: changing the 2000-char threshold, changing the attachment flow, editing core WebUI files (input-store.js is core, do not edit it).
- Never: edit files under the core framework to make the plugin work; commit secrets.

## Success Criteria
- Matrix passes in a live WebUI.
- No regression for source and podcast sends.
- No new console errors on send.

## Resolved Decisions
1. Sends REPLACE the current composer draft (matches the original intent of `inputStore.message = msg`, and matches how a user expects a canvas send to behave). Append-to-draft is a possible follow-up, not part of this fix.
2. The 2000-char attachment threshold stays unchanged.
3. A JS harness exists: `tests/test_insights_behavior.mjs` slices the store body and runs it through `new Function`. The new `tests/test_send_to_chat.mjs` reuses that pattern with fake `Alpine`/`document` globals and a proxy-layer stub.

## Implementation Record (delivered)
Changed file: `webui/open_notebook-store.js` (+33 / -27).
- `sendToChat()` small-text path now calls `_setComposerText(msg)` instead of `Alpine.store('inputStore')` plus a contenteditable `.value` write and synthetic `input` event.
- New `_composerStore()` resolves `Alpine.store('chatInput')` defensively.
- New `_setComposerText(text)` sets `composer.message`, focuses `#chat-input`, and best-effort calls `adjustTextareaHeight()` / `_setEditorCaret(length)`. When the store is missing it shows a toast ('⚠️ Chat unavailable') instead of silently dropping content.
- `_sendAsFile()` now uses `_setComposerText()` for both the 'Review the attached file: ' prompt and the no-attachment-store fallback, so neither is lost by a `.value` write.

Test file added: `tests/test_send_to_chat.mjs` (6 tests).
Observed RED before the fix: 1/6 passing (only the long-text attachment case). Observed GREEN after: 6/6.

## Verification Status
- `node --check webui/open_notebook-store.js` — pass.
- `node tests/test_send_to_chat.mjs` — 6/6 pass.
- `node tests/test_insights_behavior.mjs` — 3/3 pass (no regression).
- `pytest tests/ -q` — 97 passed, 1 failed (`test_source_insights_menu.py::test_row_menu_position_is_bound_to_the_viewport_or_row`). Proven pre-existing: the same test fails on pristine HEAD with all changes stashed.
- Live browser matrix — RUN and PASSED (Agent Zero WebUI, notebook 'Open Notebook Plugin Development', fix confirmed live via `typeof store._setComposerText === 'function'`):
  | Case | Result |
  | --- | --- |
  | Short note (40 chars) | store + DOM both hold `**📝 MATRIX short note**...` |
  | Long note (2600 chars) | 1 attachment `___MATRIX_long_note_*.md`, composer holds `Review the attached file: ` |
  | Short chat reply | store + DOM both hold the reply text |
  | Long chat reply (2600 chars) | attachment added, composer prompt filled |
  | Source | attachment added, composer prompt filled, no error |
  | Podcast episode | attachment added, composer prompt filled, no error |
- Test artifacts (2 MATRIX notes, 4 attachments) deleted/cleared after the run.
