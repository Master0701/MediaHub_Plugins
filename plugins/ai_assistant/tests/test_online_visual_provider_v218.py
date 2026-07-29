import sys
from pathlib import Path

PLUGIN_DIR = Path(__file__).resolve().parents[1]
if str(PLUGIN_DIR) not in sys.path:
    sys.path.insert(0, str(PLUGIN_DIR))

from services.providers.visual_provider import (
    VisualProvider,
    VisualProviderDisabled,
)


def _visual():
    return {
        "visual_signature": "abc123",
        "visual_fingerprint": {"frame_count": 3},
        "scene_signature": {"segment_count": 10},
        "ocr_logo_fusion": {"best_title": "STAR TREK"},
        "intro_outro_detection": {
            "intro": {"detected": True},
            "outro": {"detected": True},
        },
        "selected_frames": [
            {
                "second": 30,
                "score": 0.95,
                "position": "intro",
                "ocr_text": "STAR TREK",
                "perceptual_hashes": {
                    "ahash": "0123456789abcdef",
                    "dhash": "0011223344556677",
                    "center_dhash": "0011223344556677",
                },
            },
            {
                "second": 600,
                "score": 0.85,
                "position": "content",
                "ocr_text": None,
                "perceptual_hashes": {
                    "ahash": "fedcba9876543210",
                    "dhash": "8899aabbccddeeff",
                    "center_dhash": "8899aabbccddeeff",
                },
            },
        ],
    }


def test_provider_is_disabled_by_default():
    provider = VisualProvider()

    assert provider.status()["enabled"] is False

    try:
        provider.prepare_request(_visual(), user_approved=True)
    except VisualProviderDisabled:
        pass
    else:
        raise AssertionError("Deaktivierter Provider darf keine Anfrage erzeugen.")


def test_provider_requires_user_approval():
    provider = VisualProvider(
        enabled=True,
        endpoint="https://example.invalid/visual",
    )

    try:
        provider.prepare_request(_visual(), user_approved=False)
    except VisualProviderDisabled:
        pass
    else:
        raise AssertionError("Anfrage ohne Freigabe darf nicht erzeugt werden.")


def test_approved_request_contains_only_selected_metadata():
    provider = VisualProvider(
        enabled=True,
        endpoint="https://example.invalid/visual",
        maximum_frames=1,
    )

    payload = provider.prepare_request(
        _visual(),
        user_approved=True,
    )

    assert payload["privacy"]["user_approved"] is True
    assert payload["privacy"]["complete_video_transfer"] is False
    assert payload["privacy"]["audio_transfer"] is False
    assert len(payload["frames"]) == 1
    assert "file_path" not in payload
    assert "video" not in payload
