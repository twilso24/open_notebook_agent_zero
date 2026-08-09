# Open Notebook Plugin — Fix Tracker

## Status Legend
- ⬜ Not started
- 🔨 In progress
- ✅ Complete
- ❌ Blocked

## Fixes

| # | Fix | Priority | Status | Files |
|---|-----|----------|--------|-------|
| 1 | Proxy uses shared HTTP client | 🔴 High | ✅ | api/proxy.py, client.py |
| 2 | Unify config resolution paths | 🔴 High | ✅ | api/proxy.py, config.py |
| 3 | Proxy preserves HTTP status codes | 🔴 High | ✅ | api/proxy.py |
| 4 | Fix silent speaker injection failure | 🔴 High | ✅ | api/proxy.py |
| 5 | Add pagination to list endpoints | 🟡 Medium | ✅ | all tools |
| 6 | Per-request timeout overrides | 🟡 Medium | ✅ | client.py, api/proxy.py |
| 7 | Create test suite | 🟡 Medium | ✅ | tests/test_open_notebook.py |
| 8 | Centralized write permission helper | 🟡 Medium | ✅ | shared.py, all tools |
| 9 | Remove sys.path boilerplate | 🟢 Low | ✅ | _bootstrap.py, all tools |
| 10 | Unify default API URL | 🟢 Low | ✅ | config.py, api/proxy.py |

## Verification
- [x] All 12 files compile cleanly (`py_compile`)
- [x] All 41 unit tests pass (`unittest`)
- [ ] Live API call works (backend not accessible from container)
- [x] No regressions in existing functionality

## Files Modified

### Core Infrastructure
| File | Fixes Applied |
|------|---------------|
| `_bootstrap.py` | **NEW** — Centralized sys.path + module cache management (Fix #9) |
| `config.py` | Unified default URL comment (Fix #10) |
| `client.py` | Timeout profiles + `get_request_timeout()` (Fix #6) |
| `shared.py` | `check_write_permission()` helper (Fix #8) |

### API Layer
| File | Fixes Applied |
|------|---------------|
| `api/proxy.py` | Shared client (Fix #1), unified config (Fix #2), status preservation (Fix #3), speaker injection error surfacing (Fix #4) |

### Tools (all 6 patched)
| File | Fixes Applied |
|------|---------------|
| `tools/opennotebook_browse.py` | Bootstrap import (Fix #9), pagination (Fix #5) |
| `tools/opennotebook_manage.py` | Bootstrap import (Fix #9), write permission (Fix #8) |
| `tools/opennotebook_notes.py` | Bootstrap import (Fix #9), write permission (Fix #8), pagination (Fix #5) |
| `tools/opennotebook_sources.py` | Bootstrap import (Fix #9), write permission (Fix #8), pagination (Fix #5) |
| `tools/opennotebook_podcasts.py` | Bootstrap import (Fix #9), write permission (Fix #8), pagination (Fix #5) |
| `tools/opennotebook_query.py` | Bootstrap import (Fix #9) |

### Tests
| File | Purpose |
|------|---------|
| `tests/test_open_notebook.py` | **NEW** — 41 tests covering resolve_notebook_id, check_write_permission, prepare_content_for_backend, error handling, pagination, timeouts, and proxy unification (Fix #7) |
