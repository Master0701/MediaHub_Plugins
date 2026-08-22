import sys
from pathlib import Path

PLUGIN_DIR = Path(__file__).resolve().parents[1]
if str(PLUGIN_DIR) not in sys.path:
    sys.path.insert(0, str(PLUGIN_DIR))

from services.ocr_logo_fusion import (
    fuse_ocr_logo_hints,
    text_quality,
)
from services.visual_intelligence import VisualIntelligenceEngine


def _frame(second, score=0.9, position="intro"):
    return {
        "second": second,
        "score": score,
        "position": position,
        "metrics": {
            "sharpness": 18,
            "contrast": 170,
        },
        "perceptual_hashes": {
            "ahash": "0123456789abcdef",
            "dhash": "0011223344556677",
        },
    }


def test_text_quality_rejects_symbol_noise():
    noisy = text_quality(", & AT u“ un Owe ie = — a 9» & @")
    clean = text_quality("STAR TREK")

    assert clean["score"] > noisy["score"]
    assert clean["uppercase_ratio"] > 0.9


def test_fusion_marks_clean_intro_text_as_logo_candidate():
    result = fuse_ocr_logo_hints(
        [{"second": 30, "text": "STAR TREK"}],
        [_frame(30)],
        7200,
    )

    assert result["best_title"] == "STAR TREK"
    assert result["best_hint"]["title_candidate"] is True
    assert result["best_hint"]["logo_candidate"] is True
    assert result["object_logo_recognition"] is False


def test_fusion_rejects_garbage_ocr():
    result = fuse_ocr_logo_hints(
        [{"second": 30, "text": ", & AT u“ un Owe ie = — a 9» & @"}],
        [_frame(30)],
        7200,
    )

    assert result["candidate_count"] == 0
    assert result["rejected_count"] == 1


def test_fusion_rejects_narrative_time_cards():
    samples = (
        "18 MONTHS EARLIER",
        "3 DAYS LATER",
        "TWO YEARS AGO",
        "PRESENT DAY",
        "THE NEXT MORNING",
    )

    for text in samples:
        result = fuse_ocr_logo_hints(
            [{"second": 30, "text": text}],
            [_frame(30)],
            7200,
        )

        assert result["candidate_count"] == 0
        assert result["best_title"] is None
        assert result["rejected_count"] == 1

        rejected = result["rejected"][0]

        assert rejected["title_candidate"] is False
        assert (
            "narrative Zeit-/Handlungseinblendung, kein Titel"
            in rejected["reasons"]
        )


def test_visual_engine_contains_fusion_result():
    engine = VisualIntelligenceEngine()
    in_video = {
        "agents": {
            "frame_agent": {
                "samples": [
                    {
                        **_frame(30),
                        "metrics": {
                            "yavg": 110,
                            "contrast": 180,
                            "stddev": 45,
                            "sharpness": 18,
                            "dark_ratio": 0.02,
                            "bright_ratio": 0.01,
                        },
                    }
                ]
            },
            "ocr_agent": {
                "findings": [{"second": 30, "text": "STAR TREK"}]
            },
            "scene_agent": {"first_scene_changes": [30.0, 60.0]},
        }
    }

    result = engine.analyze(in_video, duration=7200)

    assert result["ocr_logo_fusion"]["best_title"] == "STAR TREK"
    assert result["ocr_logo_fusion"]["best_score"] >= 0.72
    assert result["privacy"]["external_transfer"] is False
