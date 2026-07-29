import sys
from pathlib import Path

PLUGIN_DIR = Path(__file__).resolve().parents[1]
if str(PLUGIN_DIR) not in sys.path:
    sys.path.insert(0, str(PLUGIN_DIR))

from services.providers.visual_provider import (
    VisualProvider,
    VisualProviderDisabled,
)
from services.visual_intelligence import VisualIntelligenceEngine
from services.visual_pipeline_validator import validate_visual_pipeline


def _sample(second, ahash, dhash, center_dhash, yavg=110, sharpness=18):
    return {
        "second": second,
        "metrics": {
            "yavg": yavg,
            "contrast": 180,
            "stddev": 45,
            "sharpness": sharpness,
            "dark_ratio": 0.02,
            "bright_ratio": 0.01,
        },
        "perceptual_hashes": {
            "ahash": ahash,
            "dhash": dhash,
            "center_dhash": center_dhash,
        },
    }


def _pipeline_result():
    engine = VisualIntelligenceEngine()
    in_video = {
        "agents": {
            "frame_agent": {
                "samples": [
                    _sample(
                        30,
                        "0123456789abcdef",
                        "0011223344556677",
                        "0011223344556677",
                    ),
                    _sample(
                        600,
                        "fedcba9876543210",
                        "8899aabbccddeeff",
                        "0011223344556676",
                        yavg=95,
                        sharpness=15,
                    ),
                    _sample(
                        7050,
                        "1234567890abcdef",
                        "1122334455667788",
                        "ffeeddccbbaa9988",
                        yavg=100,
                        sharpness=16,
                    ),
                ]
            },
            "ocr_agent": {
                "findings": [
                    {"second": 30, "text": "STAR TREK"},
                    {"second": 7050, "text": "PARAMOUNT"},
                ]
            },
            "scene_agent": {
                "first_scene_changes": [
                    15.0,
                    30.0,
                    60.0,
                    600.0,
                    3500.0,
                    7050.0,
                    7140.0,
                ]
            },
        }
    }
    return engine.analyze(in_video, duration=7200)


def test_complete_visual_pipeline_is_valid():
    result = _pipeline_result()

    assert result["pipeline_validation"]["valid"] is True
    assert result["visual_fingerprint"]["frame_count"] == 3
    assert result["scene_signature"]["state"] == "completed"
    assert result["ocr_logo_fusion"]["best_title"] == "STAR TREK"
    assert result["character_preparation"]["biometric_identification"] is False
    assert result["privacy"]["external_transfer"] is False


def test_validator_detects_inconsistent_fingerprint_count():
    result = _pipeline_result()
    result["visual_fingerprint"]["frame_count"] = 99

    validation = validate_visual_pipeline(result)

    assert validation["valid"] is False
    assert any(
        "Frameanzahl" in error
        for error in validation["errors"]
    )


def test_online_provider_remains_disabled_without_explicit_configuration():
    provider = VisualProvider()

    try:
        provider.prepare_request(
            _pipeline_result(),
            user_approved=True,
        )
    except VisualProviderDisabled:
        pass
    else:
        raise AssertionError("Provider darf standardmäßig nicht aktiv sein.")


def test_online_provider_requires_user_approval_even_when_enabled():
    provider = VisualProvider(
        enabled=True,
        endpoint="https://example.invalid/visual",
    )

    try:
        provider.prepare_request(
            _pipeline_result(),
            user_approved=False,
        )
    except VisualProviderDisabled:
        pass
    else:
        raise AssertionError("Provider darf ohne Freigabe keine Anfrage bauen.")
