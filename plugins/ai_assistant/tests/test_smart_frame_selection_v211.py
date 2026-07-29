import sys
from pathlib import Path

PLUGIN_DIR = Path(__file__).resolve().parents[1]
if str(PLUGIN_DIR) not in sys.path:
    sys.path.insert(0, str(PLUGIN_DIR))

from services.agents.frame_agent import FrameAgent
from services.agents.in_video_agent import InVideoAgent
from services.visual_intelligence import VisualIntelligenceEngine


def test_temporal_plan_covers_intro_content_and_outro():
    points = InVideoAgent._smart_sample_points(7200)

    assert 0.0 in points
    assert any(0 < point <= 180 for point in points)
    assert any(2500 <= point <= 4500 for point in points)
    assert any(point >= 7020 for point in points)
    assert len(points) <= 20


def test_frame_metrics_detect_black_and_detailed_images():
    black = bytes([0]) * FrameAgent.FRAME_BYTES
    black_metrics = FrameAgent.measure_gray_frame(black)

    pattern = bytes(
        (index * 37) % 256
        for index in range(FrameAgent.FRAME_BYTES)
    )
    pattern_metrics = FrameAgent.measure_gray_frame(pattern)

    assert black_metrics["dark_ratio"] == 1.0
    assert black_metrics["sharpness"] == 0.0
    assert pattern_metrics["contrast"] > 200
    assert pattern_metrics["sharpness"] > 10


def test_visual_engine_rejects_black_and_duplicate_frames():
    engine = VisualIntelligenceEngine()
    in_video = {
        "agents": {
            "frame_agent": {
                "samples": [
                    {
                        "second": 0,
                        "metrics": {
                            "yavg": 2,
                            "contrast": 5,
                            "stddev": 1,
                            "sharpness": 0.5,
                            "dark_ratio": 0.95,
                            "bright_ratio": 0,
                        },
                    },
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
                    },
                    {
                        "second": 60,
                        "metrics": {
                            "yavg": 111,
                            "contrast": 179,
                            "stddev": 45,
                            "sharpness": 18.2,
                            "dark_ratio": 0.02,
                            "bright_ratio": 0.01,
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
                    },
                ]
            },
            "ocr_agent": {
                "findings": [
                    {"second": 30, "text": "STAR TREK"}
                ]
            },
            "scene_agent": {
                "first_scene_changes": [30.0, 60.0, 3500.0]
            },
        }
    }

    result = engine.analyze(in_video, duration=7200)

    assert result["state"] == "completed"
    assert result["selected_count"] == 2
    assert result["selection_summary"]["duplicate_rejections"] == 1
    assert result["visual_signature"]
    assert result["privacy"]["external_transfer"] is False
