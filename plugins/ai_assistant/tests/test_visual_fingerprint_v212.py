import sys
from pathlib import Path

PLUGIN_DIR = Path(__file__).resolve().parents[1]
if str(PLUGIN_DIR) not in sys.path:
    sys.path.insert(0, str(PLUGIN_DIR))

from services.agents.frame_agent import FrameAgent
from services.visual_fingerprint import (
    compare_visual_fingerprints,
    hamming_distance,
    similarity,
)
from services.visual_intelligence import VisualIntelligenceEngine


def _pattern(offset=0):
    return bytes(
        ((index * 37) + offset) % 256
        for index in range(FrameAgent.FRAME_BYTES)
    )


def test_perceptual_hashes_are_stable_and_sensitive():
    first = FrameAgent.perceptual_hashes(_pattern(0))
    same = FrameAgent.perceptual_hashes(_pattern(0))
    changed = FrameAgent.perceptual_hashes(_pattern(17))

    assert first == same
    assert len(first["dhash"]) == 16
    assert hamming_distance(first["dhash"], same["dhash"]) == 0
    assert 0.0 <= similarity(first["dhash"], changed["dhash"]) <= 1.0


def test_multi_frame_comparison_recognizes_close_content():
    first = {
        "frame_hashes": [
            {"dhash": "0000000000000000"},
            {"dhash": "ffffffffffffffff"},
            {"dhash": "aaaaaaaaaaaaaaaa"},
        ],
        "aggregate_profile": [0.4, 0.7, 0.5],
    }
    second = {
        "frame_hashes": [
            {"dhash": "0000000000000001"},
            {"dhash": "fffffffffffffffe"},
            {"dhash": "aaaaaaaaaaaaaaab"},
        ],
        "aggregate_profile": [0.41, 0.69, 0.51],
    }

    result = compare_visual_fingerprints(first, second)

    assert result["matched_frames"] == 3
    assert result["similarity"] >= 0.90
    assert result["decision"] == "same_visual_content"


def test_visual_engine_emits_fingerprint():
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
            "scene_agent": {"first_scene_changes": [30.0, 3500.0]},
        }
    }

    result = engine.analyze(in_video, duration=7200)
    fingerprint = result["visual_fingerprint"]

    assert fingerprint["algorithm"] == "multi-frame-dhash-profile-v1"
    assert fingerprint["frame_count"] == 2
    assert len(fingerprint["aggregate_profile"]) == 6
    assert result["privacy"]["external_transfer"] is False
