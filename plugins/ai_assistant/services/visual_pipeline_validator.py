from __future__ import annotations

from typing import Any


REQUIRED_SECTIONS = (
    "selected_frames",
    "visual_fingerprint",
    "scene_signature",
    "ocr_logo_fusion",
    "character_preparation",
    "intro_outro_detection",
)


def validate_visual_pipeline(
    visual_intelligence: dict[str, Any] | None,
) -> dict[str, Any]:
    """Prüft die Konsistenz der vollständigen Visual-Intelligence-Ausgabe."""
    visual = dict(visual_intelligence or {})
    errors: list[str] = []
    warnings: list[str] = []
    checks: dict[str, bool] = {}

    for section in REQUIRED_SECTIONS:
        present = section in visual and visual.get(section) is not None
        checks[f"section:{section}"] = present
        if not present:
            errors.append(f"Pflichtbereich fehlt: {section}")

    privacy = dict(visual.get("privacy") or {})
    privacy_local = (
        privacy.get("external_transfer") is False
        and str(privacy.get("mode") or "") == "local_only"
    )
    checks["privacy:local_only"] = privacy_local
    if not privacy_local:
        errors.append("Lokaler Datenschutzstatus ist nicht eindeutig.")

    selected = list(visual.get("selected_frames") or [])
    fingerprint = dict(visual.get("visual_fingerprint") or {})
    fingerprint_count = int(fingerprint.get("frame_count") or 0)
    selected_hash_count = sum(
        bool((item.get("perceptual_hashes") or {}).get("dhash"))
        for item in selected
    )

    fingerprint_consistent = fingerprint_count == selected_hash_count
    checks["fingerprint:frame_count_consistent"] = fingerprint_consistent
    if not fingerprint_consistent:
        errors.append(
            "Visual-Fingerprint-Frameanzahl passt nicht zu den ausgewählten Hashes."
        )

    scene_signature = dict(visual.get("scene_signature") or {})
    scene_ok = (
        str(scene_signature.get("state") or "") in {"completed", "insufficient"}
        and "privacy" in scene_signature
    )
    checks["scene_signature:valid"] = scene_ok
    if not scene_ok:
        errors.append("Scene Signature ist unvollständig.")

    ocr_fusion = dict(visual.get("ocr_logo_fusion") or {})
    object_logo_recognition = bool(
        ocr_fusion.get("object_logo_recognition")
    )
    checks["ocr_logo:no_false_object_claim"] = not object_logo_recognition
    if object_logo_recognition:
        errors.append(
            "OCR-/Logo-Fusion behauptet fälschlich objektbasierte Logoerkennung."
        )

    character = dict(visual.get("character_preparation") or {})
    biometric_safe = (
        character.get("face_detection") is False
        and character.get("biometric_identification") is False
        and character.get("name_assignment") is False
    )
    checks["character_preparation:non_biometric"] = biometric_safe
    if not biometric_safe:
        errors.append(
            "Character Preparation ist nicht eindeutig nicht-biometrisch."
        )

    intro_outro = dict(visual.get("intro_outro_detection") or {})
    intro_outro_ok = (
        "intro" in intro_outro
        and "outro" in intro_outro
        and str(intro_outro.get("method") or "").startswith("multimodal_")
    )
    checks["intro_outro:valid"] = intro_outro_ok
    if not intro_outro_ok:
        errors.append("Intro-/Outro-Erkennung ist unvollständig.")

    if not selected:
        warnings.append("Keine visuellen Frames wurden ausgewählt.")
    if not visual.get("visual_signature"):
        warnings.append("Keine exakte visuelle Signatur vorhanden.")
    if not bool(visual.get("online_ready")):
        warnings.append("Visual-Intelligence-Ergebnis ist nicht online-bereit.")

    return {
        "schema_version": 1,
        "state": "valid" if not errors else "invalid",
        "valid": not errors,
        "checks": checks,
        "errors": errors,
        "warnings": warnings,
        "summary": {
            "passed_checks": sum(checks.values()),
            "failed_checks": sum(not value for value in checks.values()),
            "selected_frames": len(selected),
            "visual_fingerprint_frames": fingerprint_count,
        },
    }
