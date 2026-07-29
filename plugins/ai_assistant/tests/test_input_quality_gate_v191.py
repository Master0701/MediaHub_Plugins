import sys
from pathlib import Path

PLUGIN_DIR = Path(__file__).resolve().parents[1]
if str(PLUGIN_DIR) not in sys.path:
    sys.path.insert(0, str(PLUGIN_DIR))

from services.input_quality import evaluate_text
from services.search_variant_reasoner import SearchVariantReasoner


def test_ocr_garbage_is_rejected():
    result = evaluate_text(', & AT u“ un Owe ie = — a Sen x 9» & @ OOse', source='ocr')
    assert result.accepted is False
    assert result.score < 0.58


def test_clear_title_is_accepted():
    result = evaluate_text('Star Trek Voyager', source='ocr')
    assert result.accepted is True
    assert result.score >= 0.58


def test_low_quality_fallback_does_not_reach_search_variants():
    analysis = {
        'identification': {'title_candidate': 'pso aqua2 ts', 'media_type': 'unknown'},
        'file': {'name': 'pso-aqua2-ts-1080p.mkv'},
        'in_video': {'agents': {'ocr_agent': {'findings': [
            {'text': ', & AT u“ un Owe ie = — a Sen x 9» & @ OOse'}
        ]}}},
    }
    result = SearchVariantReasoner().build(analysis)
    titles = {item['title'].casefold() for item in result['variants']}
    assert ', & at' not in ' '.join(titles)
    assert 'aqua' not in titles
    assert result['quality_gate']['rejected']
