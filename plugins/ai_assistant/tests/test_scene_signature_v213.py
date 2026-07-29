import sys
from pathlib import Path

PLUGIN_DIR = Path(__file__).resolve().parents[1]
if str(PLUGIN_DIR) not in sys.path:
    sys.path.insert(0, str(PLUGIN_DIR))

from services.scene_signature import (
    build_scene_signature,
    compare_scene_signatures,
)
from services.visual_intelligence import VisualIntelligenceEngine


def test_scene_signature_normalizes_duration():
    first = build_scene_signature(
        [10, 20, 40, 70, 90],
        100,
        [],
    )
    second = build_scene_signature(
        [20, 40, 80, 140, 180],
        200,
        [],
    )

    comparison = compare_scene_signatures(first, second)

    assert first["segment_count"] == second["segment_count"]
    assert comparison["similarity"] >= 0.90
    assert comparison["decision"] == "same_scene_structure"


def test_scene_signature_distributes_intro_content_outro():
    signature = build_scene_signature(
        [30, 120, 600, 3000, 6500, 7100],
        7200,
        [],
    )

    assert signature["distribution"]["intro_segments"] >= 1
    assert signature["distribution"]["content_segments"] >= 1
    assert signature["distribution"]["outro_segments"] >= 1
    assert signature["scene_signature"]


def test_visual_engine_contains_scene_signature():
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
                        },
                    },
                    {
                        "second": 3500,
                        "metrics": {
                            "yavg": 90,
                            "contrast": 150,
                            "stddev": 38,
                            "sharpness": 14,
                            "dark_ratio": 0.05,
                            "bright_ratio": 0.01,
                        },
                        "perceptual_hashes": {
                            "ahash": "fedcba9876543210",
                            "dhash": "8899aabbccddeeff",
                        },
                    },
                ]
            },
            "ocr_agent": {"findings": []},
            "scene_agent": {
                "first_scene_changes": [
                    30.0,
                    60.0,
                    600.0,
                    3500.0,
                    7100.0,
                ]
            },
        }
    }

    result = engine.analyze(in_video, duration=7200)

    assert result["selected_count"] == 2
    assert result["scene_signature"]["state"] == "completed"
    assert result["scene_signature"]["segment_count"] == 6
    assert result["scene_signature"]["privacy"]["external_transfer"] is False
