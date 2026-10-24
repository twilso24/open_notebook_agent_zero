from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / 'extensions' / 'python' / 'system_prompt' / '_20_notebook_grounding.py'


def test_hook_file_exists():
    assert HOOK.exists(), 'system_prompt grounding extension file missing'


def test_hook_reads_selection_and_builds_grounding():
    src = HOOK.read_text() if HOOK.exists() else ''
    assert 'read_selection' in src
    assert 'build_grounding' in src
    assert 'selection_to_context_config' in src


def test_hook_appends_to_system_prompt_and_skips_when_empty():
    src = HOOK.read_text() if HOOK.exists() else ''
    assert 'system_prompt.append(' in src
    assert 'if not selection:' in src


def test_hook_never_calls_chat_execute():
    src = HOOK.read_text() if HOOK.exists() else ''
    assert '/api/chat/execute' not in src


def test_hook_caches_grounding_per_selection():
    src = HOOK.read_text() if HOOK.exists() else ''
    assert 'CACHE_KEY' in src
    assert 'cache' in src.lower()
