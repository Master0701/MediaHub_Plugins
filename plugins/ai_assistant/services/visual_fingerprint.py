from __future__ import annotations

from typing import Any


def hamming_distance(first: str | None, second: str | None) -> int | None:
    """Berechnet die Bitdistanz zweier gleich langer Hex-Hashes."""
    if not first or not second:
        return None
    first = str(first).strip().lower()
    second = str(second).strip().lower()
    if len(first) != len(second):
        return None
    try:
        return (int(first, 16) ^ int(second, 16)).bit_count()
    except ValueError:
        return None


def similarity(first: str | None, second: str | None) -> float:
    """Liefert 0..1 für perceptuelle Hex-Hashes."""
    distance = hamming_distance(first, second)
    if distance is None:
        return 0.0
    bits = len(str(first)) * 4
    if bits <= 0:
        return 0.0
    return round(max(0.0, 1.0 - (distance / bits)), 4)


def compare_visual_fingerprints(
    first: dict[str, Any] | None,
    second: dict[str, Any] | None,
) -> dict[str, Any]:
    """Vergleicht zwei mehrteilige visuelle Fingerprints tolerant."""
    first = first or {}
    second = second or {}

    first_frames = list(first.get("frame_hashes") or [])
    second_frames = list(second.get("frame_hashes") or [])

    pair_scores: list[float] = []
    used_second: set[int] = set()

    for first_item in first_frames:
        first_hash = first_item.get("dhash")
        best_score = 0.0
        best_index = None

        for index, second_item in enumerate(second_frames):
            if index in used_second:
                continue
            score = similarity(first_hash, second_item.get("dhash"))
            if score > best_score:
                best_score = score
                best_index = index

        if best_index is not None and best_score >= 0.72:
            used_second.add(best_index)
            pair_scores.append(best_score)

    frame_score = (
        sum(pair_scores) / max(len(first_frames), len(second_frames), 1)
    )

    first_profile = list(first.get("aggregate_profile") or [])
    second_profile = list(second.get("aggregate_profile") or [])
    profile_score = 0.0

    if (
        first_profile
        and second_profile
        and len(first_profile) == len(second_profile)
    ):
        normalized_distance = sum(
            abs(float(a) - float(b))
            for a, b in zip(first_profile, second_profile)
        ) / max(len(first_profile), 1)
        profile_score = max(0.0, 1.0 - normalized_distance)

    overall = round(
        min(1.0, (frame_score * 0.82) + (profile_score * 0.18)),
        4,
    )

    return {
        "schema_version": 1,
        "similarity": overall,
        "frame_similarity": round(frame_score, 4),
        "profile_similarity": round(profile_score, 4),
        "matched_frames": len(pair_scores),
        "first_frame_count": len(first_frames),
        "second_frame_count": len(second_frames),
        "decision": (
            "same_visual_content"
            if overall >= 0.90 and len(pair_scores) >= 3
            else "possible_same_content"
            if overall >= 0.76 and len(pair_scores) >= 2
            else "different_or_insufficient"
        ),
    }
