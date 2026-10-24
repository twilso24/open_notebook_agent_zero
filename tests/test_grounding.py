import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('grounding', ROOT / 'tools' / 'grounding.py')
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)


def test_insights_preferred_when_present():
    src = {'id': 's1', 'title': 'T', 'full_text': 'x' * 20000, 'insights': ['Summary A', 'Point B']}
    text, meta = g.build_grounding([src], budget=50000)
    assert 'Summary A' in text
    assert 'x' * 100 not in text
    assert meta['sources'][0]['mode'] == 'insights'


def test_full_text_capped_at_8000_chars():
    src = {'id': 's1', 'title': 'T', 'full_text': 'a' * 20000, 'insights': []}
    text, meta = g.build_grounding([src], budget=50000)
    assert meta['sources'][0]['mode'] == 'full'
    assert meta['sources'][0]['chars'] <= 8000


def test_hard_budget_stops_and_warns():
    srcs = [{'id': f's{i}', 'title': f'T{i}', 'full_text': 'b' * 8000, 'insights': []} for i in range(5)]
    text, meta = g.build_grounding(srcs, budget=20000)
    assert meta['total_chars'] <= 20000
    assert meta['warning']
