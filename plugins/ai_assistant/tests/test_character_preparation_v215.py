import sys
from pathlib import Path

PLUGIN_DIR = Path(__file__).resolve().parents[1]
if str(PLUGIN_DIR) not in sys.path:
    sys.path.insert(0, str(PLUGIN_DIR))

from services.agents.frame_agent import FrameAgent
from services.character_preparation import prepare_anonymous_subjects
from services.visual_intelligence import VisualIntelligenceEngine


def _selected(second, center_hash, position="content", score=0.8):
    return {
        "second": second,
        "position": position,
        "score": score,
        "metrics": {
            "yavg": 100,
            "contrast": 160,
            "stddev": 40,
            "sharpness": 16,
            "dark_ratio": 0.02,
            "bright_ratio": 0.01,
        },
        "perceptual_hashes": {
            "ahash": "0123456789abcdef",
            "dhash": "0011223344556677",
            "center_dhash": center_hash,
        },
    }


def test_frame_agent_creates_center_hash():
    raw = bytes(
        (index * 37) % 256
        for index in range(FrameAgent.FRAME_BYTES)
    )
    hashes = FrameAgent.perceptual_hashes(raw)

    assert len(hashes["center_dhash"]) == 16
    assert len(hashes["dhash"]) == 16


def test_recurring_center_motifs_are_grouped_anonymously():
    result = prepare_anonymous_subjects(
        [
            _selected(30, "0011223344556677", "intro"),
            _selected(600, "0011223344556676"),
            _selected(1200, "ffeeddccbbaa9988"),
        ]
    )

    assert result["anonymous_subject_count"] == 2
    assert result["recurring_subject_count"] == 1
    assert result["subjects"][0]["anonymous_subject_id"] == "subject-001"
    assert result["subjects"][0]["occurrence_count"] == 2
    assert result["face_detection"] is False
    assert result["biometric_identification"] is False


def test_visual_engine_contains_character_preparation():
    engine = VisualIntelligenceEngine()
    in_video = {
        "agents": {
            "frame_agent": {
                "samples": [
                    _selected(30, "0011223344556677", "intro"),
                    _selected(600, "0011223344556676"),
                ]
            },
            "ocr_agent": {"findings": []},
            "scene_agent": {"first_scene_changes": [30.0, 600.0]},
        }
    }

    result = engine.analyze(in_video, duration=7200)
    preparation = result["character_preparation"]

    assert preparation["state"] == "completed"
    assert preparation["recurring_subject_count"] == 1
    assert preparation["privacy"]["external_transfer"] is False
    assert preparation["privacy"]["biometric_data_created"] is False
