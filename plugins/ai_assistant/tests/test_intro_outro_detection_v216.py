import sys
from pathlib import Path

PLUGIN_DIR = Path(__file__).resolve().parents[1]
if str(PLUGIN_DIR) not in sys.path:
    sys.path.insert(0, str(PLUGIN_DIR))

from services.intro_outro_detection import detect_intro_outro
from services.visual_intelligence import VisualIntelligenceEngine


def test_detects_intro_from_frames_segments_and_title_text():
    result = detect_intro_outro(
        7200,
        [
            {"second": 30, "position": "intro", "score": 0.92},
            {"second": 60, "position": "intro", "score": 0.88},
        ],
        {
            "segments": [
                {"position": "intro", "normalized_length": 0.02},
                {"position": "intro", "normalized_length": 0.03},
            ],
            "rhythm": {"cuts_per_minute": 3.2},
        },
        {
            "candidates": [
                {"position": "intro", "score": 0.95, "text": "STAR TREK"}
            ]
        },
        {"subjects": []},
    )

    assert result["intro"]["detected"] is True
    assert result["intro"]["confidence"] >= 0.58
    assert result["privacy"]["external_transfer"] is False


def test_detects_outro_from_late_frames_and_text():
    result = detect_intro_outro(
        5400,
        [
            {"second": 5250, "position": "outro", "score": 0.85},
            {"second": 5370, "position": "outro", "score": 0.82},
        ],
        {
            "segments": [
                {"position": "outro", "normalized_length": 0.02},
                {"position": "outro", "normalized_length": 0.03},
            ],
            "rhythm": {"cuts_per_minute": 1.0},
        },
        {
            "candidates": [
                {"position": "outro", "score": 0.90, "text": "PARAMOUNT"}
            ]
        },
        {"subjects": []},
    )

    assert result["outro"]["detected"] is True
    assert result["outro"]["start_second"] == 5220.0


def test_weak_early_frame_is_not_blindly_called_intro():
    result = detect_intro_outro(
        7200,
        [{"second": 30, "position": "intro", "score": 0.50}],
        {"segments": [], "rhythm": {"cuts_per_minute": 0.0}},
        {"candidates": []},
        {"subjects": []},
    )

    assert result["intro"]["detected"] is False


def test_visual_engine_contains_intro_outro_result():
    engine = VisualIntelligenceEngine()
    in_video = {
        "agents": {
            "frame_agent": {
                "samples": [
                    {
                        "second": 30,
                        "metrics": {
                            "yavg": 110,
                            "contrast": 180,
                            "stddev": 45,
                            "sharpness": 18,
                            "dark_ratio": 0.02,
                            "bright_ratio": 0.01,
                        },
                        "perceptual_hashes": {
                            "ahash": "0123456789abcdef",
                            "dhash": "0011223344556677",
                            "center_dhash": "0011223344556677",
                        },
                    },
                    {
                        "second": 60,
                        "metrics": {
                            "yavg": 100,
                            "contrast": 170,
                            "stddev": 42,
                            "sharpness": 17,
                            "dark_ratio": 0.02,
                            "bright_ratio": 0.01,
                        },
                        "perceptual_hashes": {
                            "ahash": "1123456789abcdef",
                            "dhash": "1011223344556677",
                            "center_dhash": "1011223344556677",
                        },
                    },
                ]
            },
            "ocr_agent": {
                "findings": [{"second": 30, "text": "STAR TREK"}]
            },
            "scene_agent": {
                "first_scene_changes": [15.0, 30.0, 60.0, 90.0]
            },
        }
    }

    result = engine.analyze(in_video, duration=7200)

    assert "intro_outro_detection" in result
    assert result["intro_outro_detection"]["intro"]["confidence"] > 0
    assert result["intro_outro_detection"]["privacy"]["external_transfer"] is False
