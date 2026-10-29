# Source Menu and Insights Spec

## Status

Draft. Causes below come from code reading and screenshots. They are not yet reproduced in a live browser.

## Problem

The source row menu (three-dot button) has three defects:

1. Tapping Insights shows 'Please select a transformation first.' instead of the source's insights.
2. There is no way to create an insight from a preset inside the Insights view.
3. Insight presets (transformations) sit in the Sources tab as a dropdown. They belong with insights, not sources.

The menu is also clipped in the mobile layout, which hides Related, A0 Chat, and Delete.

## Goals

- Insights opens a list of the source's existing insights.
- From that list, the user can create a new insight by choosing a preset (transformation) defined in the app.
- Presets are managed and selected inside the Insights view, not in the Sources tab.
- The source menu is fully visible on mobile and desktop.

## Non-Goals

- Changing how transformations are defined in Open Notebook.
- Changing the chat context selector (Off / Full text / Insights).
- Auto-generating insights on import.

## Current Behavior (after the fix, commit a9fada9 plus uncommitted store fixes)

- Sources tab: no transformation dropdown. Only the import control.
- Row menu (canvas-panel.html): Details, Chat, Insights, Related, A0 Chat, Delete. It uses `position:fixed` with a `_menuPos` clamped to the viewport, so all items stay reachable at 390px.
- getSourceInsights(sourceId): loads existing insights only, with no preset requirement. Sets per-source `insightsLoading[sourceId]` and `insightsError[sourceId]` instead of global `loading`/`error`. A non-OK response now raises a visible error instead of an empty list.
- createSourceInsight(sourceId, presetId): requires both ids; rejects while that source already has a generation in flight. It snapshots existing insight IDs before the POST and polls up to 30 times at 2 s, succeeding only when a new insight ID appears. On 60 s it raises a visible timeout error.
- loadTransformations(): sets `presetsError` on failure instead of failing silently, and selects the default or first preset into `selectedPresetId`.
- Insights panel (canvas-panel.html): shows a preset `<select>` bound to `selectedPresetId`, a Create insight button disabled until a preset is chosen, a per-source spinner, an error line, and a Retry button for preset load failures.
- Insight rows show `insight.insight_type`, which matches the API response, falling back to 'Insight'.
- Insight content renders through `md()`, which escapes `&`, `<`, and `>` before applying markdown rules.
- Insight data is shared through `insightCache` in open_notebook-store.js. a0-context-store-v2.js delegates to it when the main store is loaded and keeps a direct-fetch fallback for when it is not.

## Requirements

### R1 Insights list
- R1.1 Insights opens a panel for the chosen source listing its existing insights.
- R1.2 Each insight shows its type or preset name, a short preview, and an expand control for full content.
- R1.3 Existing insights are shown even when no transformation is selected.
- R1.4 Empty state: 'No insights yet for this source' with the create control visible.

### R2 Create from preset
- R2.1 The Insights panel has a Create insight control with a preset picker.
- R2.2 Presets come from GET /api/transformations. The default preset (apply_default) is preselected.
- R2.3 Creating posts to /api/sources/{id}/insights with the chosen transformation_id.
- R2.4 While generating, show a per-source loading state. Do not use the global loading flag.
- R2.5 On completion, show the new insight. On timeout or error, show a message with a retry action.
- R2.6 Polling stops on success, error, or timeout, and the timeout is shown to the user.

### R3 Presets move out of Sources
- R3.1 Remove the transformation dropdown from the Sources tab.
- R3.2 Presets appear only in the Insights panel (picker and, optionally, a preset list).
- R3.3 Selecting a preset is local to the Insights panel and does not affect other sources.

### R4 Preset loading
- R4.1 Load presets when the Insights panel opens, not only when the main panel opens.
- R4.2 On failure, show an error with a retry action and an empty-state message in the picker. Do not fail silently.

### R5 Source menu
- R5.1 The row menu is fully visible on mobile (no clipping by the scroll pane).
- R5.2 Use fixed or teleported positioning anchored to the row button, flipping above when near the bottom edge.
- R5.3 Remove the unused _menuPos code or use it.
- R5.4 Keep one entry point for Insights. Remove the duplicate from the source detail view or make it open the same panel.

### R6 Labels and data
- R6.1 Insight labels use insight_type (or the API's equivalent) and fall back to 'Insight'. Confirm the field names from a live /api/sources/{id}/insights response before implementing.

## Acceptance Criteria

- AC1 With no transformation preselected, tapping Insights on a source with existing insights lists them. No 'Please select a transformation first' error appears.
- AC2 Tapping Insights on a source with no insights shows an empty state with a Create control.
- AC3 Creating an insight with a chosen preset shows a spinner for that source, then the new insight. Other rows are not affected.
- AC4 The Sources tab has no transformation dropdown.
- AC5 On a 390 px wide mobile viewport, every row menu item (Details, Chat, Insights, Related, A0 Chat, Delete) is reachable.
- AC6 With the API unreachable, the Insights panel shows an error and a retry action, not a blank list.
- AC7 Polling ends within 60 seconds with either results or a timeout message.

## Design Notes

- Keep state per source (insightsBySource, insightsLoading[sourceId], insightsError[sourceId]) instead of the global loading flag.
- Consolidate insight state into one store. webui/a0-context-store-v2.js and webui/open_notebook-store.js both hold insight data today.
- Reuse the existing md() renderer for insight content.

## Decisions

1. Presets are shown as a browsable list in the Insights panel, not only as a picker.
2. Insight generation is blocked per source while one is running. Other sources are not blocked.
3. Consolidating insight state from webui/a0-context-store-v2.js into one store is deferred to a follow-up.

## Open Questions

1. Confirmed from GET /api/sources/{id}/insights: each item has id, source_id, insight_type, and content. There is no title or name field, so canvas-panel.html:304 always falls back to 'Insight'. Use insight_type for the label and content for the body. The live browser reproduction of the Insights error is still pending.

## Implementation Status

Implemented in webui/open_notebook-store.js and webui/canvas-panel.html. The 'Current Behavior' section above describes the code before this change.

- Insights loads existing insights without a preset (AC1). The preset check runs only when generating.
- Presets are a browsable list inside the Insights panel. The Sources-tab dropdown is removed (AC4).
- createSourceInsight posts the chosen transformation_id and polls up to 60 seconds with a visible timeout (AC3, AC7).
- Loading and errors are per source (insightsLoading, insightsError).
- Presets load when the Insights panel opens. A failed load shows presetsError with a Retry action (R4).
- Insight rows label with insight_type (R6.1).
- The row menu is anchored to its trigger through `_menuPos` with `position: fixed`, flipped above the row when there is no room below, and clamped to both the viewport and the clipping scroll pane (R5.2, R5.3 resolved by *using* `_menuPos`). Verified at 390 px.
- The duplicate Insights button in source detail is removed (R5.4).

Verification status:
- node --check passes for the store. canvas-panel.html parses as HTML.
- 8 contract tests in tests/test_source_insights_menu.py pass.
- tests/ is tracked (20 test files); the earlier note that it was gitignored was wrong and is withdrawn.
- AC5 is closed: the row menu was checked at 390 px with a real pointer click, not a synthetic one.

### Post-release defects found on a real phone (0.5.2)

Three separate faults made the row menu open low, get clipped, or not open at all. Each had a failing test first.

1. **Containing-block offset.** The core `.modal-inner` carries a `transform`, which makes it the containing block for `position: fixed`. Viewport coordinates were applied inside that box, so the menu rendered 102 px too low (computed `top: 621` drew at `723`). Fixed with `_containingBlockOffset()` / `_toLocalMenuPos()`.
2. **Menu never measured, so it never flipped.** `_findRowMenu` looked on `btn.parentElement`, but the menu lives on `.on-list-item`. The height fell back to `0`, the flip-above never engaged, and the scroll pane's `overflow: hidden auto` clipped the lower items. Fixed by searching the row ancestor and by clamping to the pane as well as the viewport.
3. **Version skew (mobile only).** The panel HTML was served versioned while it imported the store over an unversioned URL, and `sw.js` caches by exact request URL. A phone could run new panel HTML against a cached old store, where `_openRowMenu` did not exist: the tap threw, `_activeMenuId` was never set, and no menu appeared at all. Reproduced by shadowing `_openRowMenu` on a live page and clicking (no menu, `mutationCount: 0`). Both assets now move together, enforced by `tests/test_asset_versioning.py`.

Two further fixes: the close guard is now target-based rather than a 250 ms window (mobile tap-to-click delay could close a menu the tap had just opened), and `_measureMenu` restores its temporary off-screen style in a `finally` block so a thrown layout read cannot leave the menu invisible.

Tests: `tests/test_menu_placement.mjs` (20) and `tests/test_asset_versioning.py` (2) are behavior/contract tests; the pre-existing 8 string checks remain.

Open follow-up: `webui/js/extensions.js:99` imports extension modules unversioned, so the script that supplies `modalPath` can itself come from cache and advertise a stale panel URL. The panel content is still correct in that case, but the URL is not a reliable identifier. Core-side change, tracked separately.

## Verification Plan

- Partial live browser check on 2026-10-26: the source menu showed all 6 items; the Insights panel listed the existing insight without a preset (AC1) and showed the preset list and Create insight button (AC3).
- Not verified: the 390px menu fit (AC5), since the mobile geometry probe returned zero-size rects; a clean console, since no console capture was installed; and the create-generation flow end to end.
- Update tests that assert on the Sources-tab dropdown or the global loading flag. Do not weaken them.
- Add tests for: insights listed without a selected preset, create-from-preset request body, per-source loading, and menu positioning on a narrow viewport.
- Manual check on the mobile viewport and a desktop viewport.

## Out of Scope For This Spec

- Podcast and notes tabs.
- Chat context selector behavior.
