# Spec: Button Text Contrast and Hover

## Objective
The two action buttons in the Open Notebook canvas panel ("+ New Notebook" and "Generate Podcast") must look consistent, and the "+ New Notebook" label must stay readable on hover.

User stories:
- As a user, both top action buttons show black label text at rest, so they look like a matched pair.
- As a user, hovering "+ New Notebook" keeps its label visible (black text on blue background).

## Root Cause
- `webui/open_notebook.css`: `.on-btn:hover` sets `color: var(--color-highlight)`. Because it has higher specificity than `.on-btn--primary`, the primary button's text becomes the same blue as its background on hover.
- `webui/canvas-panel.html`: "Generate Podcast" sets inline `color:white`, while "+ New Notebook" uses the primary class with theme-dependent text color. The labels therefore differ.

## Commands
- Test: `/opt/venv/bin/python -m pytest tests/test_button_styles.py -v`
- Full plugin tests: `/opt/venv/bin/python -m pytest tests -v`

## Project Structure
- `webui/open_notebook.css`: shared button styles (edit here)
- `webui/canvas-panel.html`: button markup (inline style on Generate Podcast)
- `tests/test_button_styles.py`: CSS/markup contract tests (new)
- `docs/specs/`: specs for this plugin

## Code Style
Small, scoped CSS rules with explicit colors. Prefer a class over inline styles when a color must be shared.

```css
.on-btn--primary:hover {
  color: #000;
}
```

## Testing Strategy
- Framework: pytest (no existing test suite in the repo; tests are added with this change).
- Tests read the CSS and HTML files and assert the rules that matter, with expected values written independently of the implementation.
- Required checks:
  1. `.on-btn--primary` text color is black (`#000`) at rest.
  2. `.on-btn--primary:hover` keeps text color black, so it is not overridden by `.on-btn:hover`.
  3. "Generate Podcast" button text color is black, not white.
  4. Both buttons share black label text, so they match.
- Each new test must fail before the fix (RED) and pass after (GREEN).

## Boundaries
- Always: write the failing test first; run the affected tests after the last edit; keep changes limited to the two defects.
- Ask first: changing the button background colors, adding dependencies, or committing and pushing.
- Never: weaken or delete tests to make them pass; revert unrelated uncommitted changes in the repo.

## Success Criteria
- All new tests in `tests/test_button_styles.py` fail before the fix and pass after it.
- The rendered "+ New Notebook" label stays black on hover.
- "Generate Podcast" label is black at rest and on hover.
- No other CSS rules change.

## Open Questions
- Should both buttons keep their current background colors (blue and rose)? Assumed yes.
