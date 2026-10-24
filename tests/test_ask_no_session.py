from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = (ROOT / 'tools' / 'opennotebook_chat.py').read_text()


def _ask_body():
    return TOOL[TOOL.index('async def _ask('):TOOL.index('async def _history(')]


def test_ask_does_not_create_chat_session():
    body = _ask_body()
    assert '_create_session' not in body, 'ask must answer from grounding without a chat session'
    assert '/api/chat/sessions' not in body


def test_new_session_still_creates_session():
    assert 'async def _new_session(' in TOOL
    new_body = TOOL[TOOL.index('async def _new_session('):TOOL.index('async def _search(')]
    assert '_create_session' in new_body


def test_history_still_reads_session():
    assert '/api/chat/sessions/{session_id}' in TOOL
