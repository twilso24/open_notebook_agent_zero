from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = (ROOT / 'tools' / 'opennotebook_chat.py').read_text()


def test_ask_does_not_call_chat_execute():
    ask = TOOL[TOOL.index('async def _ask('):TOOL.index('async def _history(')]
    assert '/api/chat/execute' not in ask, 'ask must answer from grounding, not spend notebook LLM tokens'


def test_ask_uses_grounding_builder():
    assert 'build_grounding' in TOOL
