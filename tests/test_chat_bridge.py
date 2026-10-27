from pathlib import Path

TOOL = Path(__file__).resolve().parents[1] / 'tools' / 'opennotebook_chat.py'


def test_chat_bridge_tool_exists():
    assert TOOL.exists(), 'tools/opennotebook_chat.py must exist before the bridge is usable'


def test_execute_context_is_object_not_string():
    src = TOOL.read_text() if TOOL.exists() else ''
    assert '"context"' in src and 'str(' not in src.split('context')[1][:40], 'context must be sent as a JSON object'


def test_context_config_maps_insights_and_full_content():
    src = TOOL.read_text() if TOOL.exists() else ''
    assert "'insights'" in src or '"insights"' in src
    assert 'full content' in src
    assert 'not in' in src
