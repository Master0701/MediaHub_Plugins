from __future__ import annotations

from typing import Any


def _bounded(value: float) -> float:
    return round(max(0.0, min(1.0, value)), 4)


def _segment_support(
    segments: list[dict[str, Any]],
    position: str,
) -> dict[str, Any]:
    matching = [
        item for item in segments
        if str(item.get("position") or "") == position
    ]
    lengths = [
        float(item.get("normalized_length") or 0.0)
        for item in matching
    ]
    return {
        "count": len(matching),
        "normalized_duration": round(sum(lengths), 5),
        "average_normalized_length": round(
            sum(lengths) / len(lengths),
            5,
        ) if lengths else 0.0,
    }


def detect_intro_outro(
    duration: float,
    selected_frames: list[dict[str, Any]] | None,
    scene_signature: dict[str, Any] | None,
    ocr_logo_fusion: dict[str, Any] | None,
    character_preparation: dict[str, Any] | None,
) -> dict[str, Any]:
    """Erkennt wahrscheinliche Intro-/Outro-Bereiche aus lokalen Hinweisen."""
    duration = max(0.0, float(duration or 0.0))
    selected_frames = list(selected_frames or [])
    scene_signature = scene_signature or {}
    ocr_logo_fusion = ocr_logo_fusion or {}
    character_preparation = character_preparation or {}

    segments = list(scene_signature.get("segments") or [])
    intro_frames = [
        frame for frame in selected_frames
        if str(frame.get("position") or "") == "intro"
    ]
    outro_frames = [
        frame for frame in selected_frames
        if str(frame.get("position") or "") == "outro"
    ]

    intro_segment_support = _segment_support(segments, "intro")
    outro_segment_support = _segment_support(segments, "outro")

    candidates = list(ocr_logo_fusion.get("candidates") or [])
    intro_text = [
        item for item in candidates
        if str(item.get("position") or "") == "intro"
    ]
    outro_text = [
        item for item in candidates
        if str(item.get("position") or "") == "outro"
    ]

    recurring_subjects = [
        item for item in (character_preparation.get("subjects") or [])
        if bool(item.get("recurring"))
    ]
    recurring_intro = sum(
        "intro" in set(item.get("positions") or [])
        for item in recurring_subjects
    )
    recurring_outro = sum(
        "outro" in set(item.get("positions") or [])
        for item in recurring_subjects
    )

    intro_score = 0.0
    intro_reasons: list[str] = []
    if intro_frames:
        intro_score += min(0.28, len(intro_frames) * 0.07)
        intro_reasons.append("hochwertige frühe Frames")
    if intro_segment_support["count"] >= 2:
        intro_score += 0.18
        intro_reasons.append("mehrere frühe Szenensegmente")
    if intro_text:
        intro_score += min(
            0.36,
            max(float(item.get("score") or 0.0) for item in intro_text) * 0.36,
        )
        intro_reasons.append("Titel-/Logo-Text im frühen Bereich")
    if recurring_intro:
        intro_score += min(0.12, recurring_intro * 0.04)
        intro_reasons.append("wiederkehrendes Zentralmotiv im frühen Bereich")
    if (
        float((scene_signature.get("rhythm") or {}).get("cuts_per_minute") or 0.0)
        >= 2.0
    ):
        intro_score += 0.06
        intro_reasons.append("erkennbare Schnittfolge")

    outro_score = 0.0
    outro_reasons: list[str] = []
    if outro_frames:
        outro_score += min(0.24, len(outro_frames) * 0.06)
        outro_reasons.append("hochwertige späte Frames")
    if outro_segment_support["count"] >= 2:
        outro_score += 0.18
        outro_reasons.append("mehrere späte Szenensegmente")
    if outro_text:
        outro_score += min(
            0.38,
            max(float(item.get("score") or 0.0) for item in outro_text) * 0.38,
        )
        outro_reasons.append("Text-/Studiohinweis im späten Bereich")
    if recurring_outro:
        outro_score += min(0.10, recurring_outro * 0.04)
        outro_reasons.append("wiederkehrendes Zentralmotiv im späten Bereich")
    if duration >= 1200 and outro_frames:
        outro_score += 0.06
        outro_reasons.append("plausibler Abspannbereich bei längerer Laufzeit")

    intro_score = _bounded(intro_score)
    outro_score = _bounded(outro_score)

    intro_detected = intro_score >= 0.58
    outro_detected = outro_score >= 0.54

    intro_end = (
        round(min(180.0, duration * 0.12), 2)
        if duration
        else None
    )
    outro_start = (
        round(max(0.0, duration - 180.0), 2)
        if duration
        else None
    )

    return {
        "schema_version": 1,
        "state": "completed",
        "method": "multimodal_intro_outro_heuristic_v1",
        "intro": {
            "detected": intro_detected,
            "confidence": intro_score,
            "start_second": 0.0 if intro_detected else None,
            "end_second": intro_end if intro_detected else None,
            "frame_count": len(intro_frames),
            "text_candidate_count": len(intro_text),
            "segment_support": intro_segment_support,
            "reasons": intro_reasons,
        },
        "outro": {
            "detected": outro_detected,
            "confidence": outro_score,
            "start_second": outro_start if outro_detected else None,
            "end_second": round(duration, 2) if outro_detected and duration else None,
            "frame_count": len(outro_frames),
            "text_candidate_count": len(outro_text),
            "segment_support": outro_segment_support,
            "reasons": outro_reasons,
        },
        "limitations": [
            "Die Bereiche sind heuristische Kandidaten und keine framegenaue Schnittmarkierung.",
            "Serienintro, Studiologo, Rückblick und Titelkarte können sich überschneiden.",
            "Eine spätere lernende Referenzdatenbank kann die Grenzen präzisieren.",
        ],
        "privacy": {
            "mode": "local_only",
            "external_transfer": False,
        },
    }
