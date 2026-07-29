from __future__ import annotations

import hashlib
import json
import math
from typing import Any


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def _position(normalized: float) -> str:
    if normalized <= 0.12:
        return "intro"
    if normalized >= 0.88:
        return "outro"
    return "content"


def _nearest_visual_frame(
    normalized_time: float,
    visual_frames: list[dict[str, Any]],
) -> dict[str, Any] | None:
    if not visual_frames:
        return None
    return min(
        visual_frames,
        key=lambda item: abs(
            float(item.get("normalized_time") or 0.0) - normalized_time
        ),
    )


def build_scene_signature(
    scene_changes: list[float] | None,
    duration: float,
    selected_frames: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Erzeugt eine laufzeitunabhängige Signatur aus Szenenrhythmus und Frames."""
    duration = max(0.0, float(duration or 0.0))
    raw_changes = sorted(
        {
            round(float(value), 3)
            for value in (scene_changes or [])
            if float(value) >= 0
            and (duration <= 0 or float(value) <= duration)
        }
    )

    if duration <= 0:
        inferred = raw_changes[-1] if raw_changes else 0.0
        duration = max(inferred, 1.0)

    boundaries = [0.0, *raw_changes, duration]
    boundaries = sorted(
        {
            round(_clamp(value, 0.0, duration), 3)
            for value in boundaries
        }
    )

    visual_frames: list[dict[str, Any]] = []
    for frame in selected_frames or []:
        second = float(frame.get("second") or 0.0)
        hashes = frame.get("perceptual_hashes") or {}
        visual_frames.append(
            {
                "second": round(second, 3),
                "normalized_time": round(
                    _clamp(second / duration, 0.0, 1.0),
                    5,
                ),
                "dhash": hashes.get("dhash"),
                "ahash": hashes.get("ahash"),
                "score": float(frame.get("score") or 0.0),
            }
        )

    segments: list[dict[str, Any]] = []
    for index in range(len(boundaries) - 1):
        start = boundaries[index]
        end = boundaries[index + 1]
        length = max(0.0, end - start)
        if length <= 0:
            continue

        midpoint = start + (length / 2)
        normalized_start = start / duration
        normalized_end = end / duration
        normalized_mid = midpoint / duration
        nearest = _nearest_visual_frame(normalized_mid, visual_frames)

        segments.append(
            {
                "index": len(segments),
                "start": round(start, 3),
                "end": round(end, 3),
                "length": round(length, 3),
                "normalized_start": round(normalized_start, 5),
                "normalized_end": round(normalized_end, 5),
                "normalized_length": round(length / duration, 5),
                "position": _position(normalized_mid),
                "visual_dhash": (
                    nearest.get("dhash") if nearest else None
                ),
                "visual_distance": (
                    round(
                        abs(
                            float(nearest["normalized_time"])
                            - normalized_mid
                        ),
                        5,
                    )
                    if nearest
                    else None
                ),
            }
        )

    lengths = [segment["length"] for segment in segments]
    average_length = (
        sum(lengths) / len(lengths)
        if lengths
        else duration
    )
    variance = (
        sum((value - average_length) ** 2 for value in lengths)
        / len(lengths)
        if lengths
        else 0.0
    )
    rhythm_stddev = math.sqrt(variance)

    # Quantized normalized scene pattern: robust against small timing drift.
    rhythm_bins = [
        min(15, max(0, round(segment["normalized_length"] * 128)))
        for segment in segments[:128]
    ]
    position_pattern = [
        {"intro": 0, "content": 1, "outro": 2}[segment["position"]]
        for segment in segments[:128]
    ]
    visual_pattern = [
        segment["visual_dhash"]
        for segment in segments
        if segment.get("visual_dhash")
    ][:32]

    signature_payload = {
        "rhythm_bins": rhythm_bins,
        "position_pattern": position_pattern,
        "visual_pattern": visual_pattern,
    }
    signature = hashlib.sha256(
        json.dumps(
            signature_payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()

    return {
        "schema_version": 1,
        "state": "completed" if segments else "insufficient",
        "algorithm": "normalized-scene-rhythm-visual-v1",
        "duration": round(duration, 3),
        "scene_change_count": len(raw_changes),
        "segment_count": len(segments),
        "segments": segments,
        "rhythm": {
            "average_scene_length": round(average_length, 3),
            "scene_length_stddev": round(rhythm_stddev, 3),
            "cuts_per_minute": round(
                (len(raw_changes) / duration) * 60,
                3,
            ),
            "rhythm_bins": rhythm_bins,
        },
        "distribution": {
            "intro_segments": sum(
                segment["position"] == "intro"
                for segment in segments
            ),
            "content_segments": sum(
                segment["position"] == "content"
                for segment in segments
            ),
            "outro_segments": sum(
                segment["position"] == "outro"
                for segment in segments
            ),
        },
        "visual_hash_count": len(visual_pattern),
        "scene_signature": signature,
        "signature_payload": signature_payload,
        "privacy": {
            "mode": "local_only",
            "external_transfer": False,
        },
    }


def compare_scene_signatures(
    first: dict[str, Any] | None,
    second: dict[str, Any] | None,
) -> dict[str, Any]:
    """Vergleicht normalisierte Szenenrhythmen tolerant."""
    first = first or {}
    second = second or {}
    first_bins = list(
        ((first.get("rhythm") or {}).get("rhythm_bins") or [])
    )
    second_bins = list(
        ((second.get("rhythm") or {}).get("rhythm_bins") or [])
    )

    if not first_bins or not second_bins:
        return {
            "schema_version": 1,
            "similarity": 0.0,
            "decision": "insufficient",
        }

    common = min(len(first_bins), len(second_bins))
    length_ratio = common / max(len(first_bins), len(second_bins))
    distance = sum(
        abs(first_bins[index] - second_bins[index])
        for index in range(common)
    )
    rhythm_similarity = max(
        0.0,
        1.0 - (distance / max(common * 15, 1)),
    )

    first_rate = float(
        (first.get("rhythm") or {}).get("cuts_per_minute") or 0.0
    )
    second_rate = float(
        (second.get("rhythm") or {}).get("cuts_per_minute") or 0.0
    )
    rate_similarity = (
        1.0
        if max(first_rate, second_rate) == 0
        else max(
            0.0,
            1.0
            - abs(first_rate - second_rate)
            / max(first_rate, second_rate),
        )
    )

    similarity = round(
        (rhythm_similarity * 0.65)
        + (length_ratio * 0.20)
        + (rate_similarity * 0.15),
        4,
    )

    return {
        "schema_version": 1,
        "similarity": similarity,
        "rhythm_similarity": round(rhythm_similarity, 4),
        "segment_count_similarity": round(length_ratio, 4),
        "cut_rate_similarity": round(rate_similarity, 4),
        "decision": (
            "same_scene_structure"
            if similarity >= 0.90
            else "possible_same_structure"
            if similarity >= 0.74
            else "different_scene_structure"
        ),
    }
