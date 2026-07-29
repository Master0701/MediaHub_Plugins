from __future__ import annotations

import hashlib
import json
from typing import Any

from services.visual_fingerprint import compare_visual_fingerprints
from services.visual_pipeline_validator import validate_visual_pipeline
from services.character_preparation import prepare_anonymous_subjects
from services.intro_outro_detection import detect_intro_outro
from services.ocr_logo_fusion import fuse_ocr_logo_hints
from services.scene_signature import (
    build_scene_signature,
    compare_scene_signatures,
)


class VisualIntelligenceEngine:
    """Bewertet lokale Frames und wählt aussagekräftige Kandidaten aus."""

    @staticmethod
    def _position_label(second: float, duration: float) -> str:
        if not duration:
            return "unknown"
        if second <= min(180.0, duration * 0.12):
            return "intro"
        if second >= max(0.0, duration - 180.0):
            return "outro"
        return "content"

    @staticmethod
    def _distance(first: list[float], second: list[float]) -> float:
        if not first or not second or len(first) != len(second):
            return 999.0
        return sum(abs(a - b) for a, b in zip(first, second))

    def analyze(
        self,
        in_video: dict[str, Any],
        duration: float = 0.0,
    ) -> dict[str, Any]:
        agents = in_video.get("agents") or {}
        frame_data = agents.get("frame_agent") or {}
        ocr_data = agents.get("ocr_agent") or {}
        scene_data = agents.get("scene_agent") or {}

        samples = list(frame_data.get("samples") or [])
        ocr_by_second = {
            round(float(item.get("second") or 0), 2):
            str(item.get("text") or "").strip()
            for item in (ocr_data.get("findings") or [])
        }

        ranked: list[dict[str, Any]] = []

        for sample in samples:
            metrics = sample.get("metrics") or {}
            if not metrics:
                continue

            second = round(float(sample.get("second") or 0), 2)
            average = float(metrics.get("yavg") or 0)
            contrast = float(
                metrics.get("contrast")
                or (
                    float(metrics.get("ymax") or 0)
                    - float(metrics.get("ymin") or 0)
                )
            )
            sharpness_value = metrics.get("sharpness")
            sharpness_measured = sharpness_value is not None

            deviation = float(metrics.get("stddev") or 0)

            if sharpness_measured:
                sharpness = float(sharpness_value or 0)
            else:
                # Rückwärtskompatibilität für ältere Frame-Agent-Ergebnisse.
                # Fehlende Schärfe darf nicht wie ein bestätigtes unscharfes
                # Bild behandelt werden.
                sharpness = (
                    8.0
                    if contrast >= 55
                    else 5.0
                    if contrast >= 30
                    else 0.0
                )
            dark_ratio = float(metrics.get("dark_ratio") or 0)
            bright_ratio = float(metrics.get("bright_ratio") or 0)
            text = ocr_by_second.get(second, "")
            position = self._position_label(second, duration)

            score = 0.0
            reasons: list[str] = []

            if 22 <= average <= 232:
                score += 0.20
                reasons.append("brauchbare Helligkeit")
            else:
                reasons.append("problematische Helligkeit")

            if contrast >= 55:
                score += 0.20
                reasons.append("deutlicher Kontrast")
            elif contrast >= 30:
                score += 0.10
                reasons.append("mittlerer Kontrast")

            if sharpness_measured and sharpness >= 12:
                score += 0.25
                reasons.append("hohe Bildschärfe")
            elif sharpness >= 6:
                score += 0.12
                reasons.append(
                    "brauchbare Bildschärfe"
                    if sharpness_measured
                    else "Schärfe aus älteren Messwerten abgeschätzt"
                )
            elif sharpness_measured:
                reasons.append("wahrscheinlich unscharf")
            else:
                reasons.append("keine direkte Schärfemessung vorhanden")

            if deviation >= 28:
                score += 0.10
                reasons.append("reicher Bildinhalt")

            if text and len(text) >= 4:
                score += 0.20
                reasons.append("OCR-/Titelhinweis")

            if position == "intro":
                score += 0.08
                reasons.append("Intro-/Titelkartenbereich")
            elif position == "outro":
                score += 0.05
                reasons.append("Abspann-/Studiobereich")

            if dark_ratio >= 0.82:
                score -= 0.55
                reasons.append("überwiegend Schwarzbild")
            if bright_ratio >= 0.82:
                score -= 0.45
                reasons.append("überwiegend Weißbild")

            vector = [
                round(average / 255, 4),
                round(contrast / 255, 4),
                round(min(sharpness / 40, 1.0), 4),
                round(min(deviation / 100, 1.0), 4),
                round(dark_ratio, 4),
                round(bright_ratio, 4),
            ]
            perceptual_hashes = dict(
                sample.get("perceptual_hashes") or {}
            )

            accepted = (
                score >= 0.48
                and dark_ratio < 0.82
                and bright_ratio < 0.82
                and sharpness >= 4
            )

            ranked.append(
                {
                    "second": second,
                    "score": round(max(0.0, min(1.0, score)), 3),
                    "accepted": accepted,
                    "position": position,
                    "reasons": reasons,
                    "metrics": metrics,
                    "ocr_text": text or None,
                    "visual_vector": vector,
                    "perceptual_hashes": perceptual_hashes,
                }
            )

        ranked.sort(
            key=lambda item: (
                item["accepted"],
                item["score"],
            ),
            reverse=True,
        )

        selected: list[dict[str, Any]] = []
        duplicate_rejections: list[dict[str, Any]] = []

        for candidate in ranked:
            if not candidate["accepted"]:
                continue

            duplicate = any(
                candidate.get("position") == selected_item.get("position")
                and self._distance(
                    candidate["visual_vector"],
                    selected_item["visual_vector"],
                ) < 0.12
                for selected_item in selected
            )

            if duplicate:
                rejected = dict(candidate)
                rejected["accepted"] = False
                rejected["reasons"] = [
                    *candidate["reasons"],
                    "zu ähnlich zu einem höher bewerteten Frame",
                ]
                duplicate_rejections.append(rejected)
                continue

            selected.append(candidate)
            if len(selected) >= 10:
                break

        frame_hashes = [
            {
                "second": item["second"],
                "position": item["position"],
                "score": item["score"],
                "ahash": (
                    item.get("perceptual_hashes") or {}
                ).get("ahash"),
                "dhash": (
                    item.get("perceptual_hashes") or {}
                ).get("dhash"),
            }
            for item in selected
            if (item.get("perceptual_hashes") or {}).get("dhash")
        ]

        aggregate_profile = []
        if selected:
            vector_length = len(selected[0].get("visual_vector") or [])
            for index in range(vector_length):
                values = [
                    float(item["visual_vector"][index])
                    for item in selected
                    if len(item.get("visual_vector") or []) > index
                ]
                aggregate_profile.append(
                    round(sum(values) / len(values), 4)
                    if values
                    else 0.0
                )

        visual_fingerprint = {
            "schema_version": 1,
            "algorithm": "multi-frame-dhash-profile-v1",
            "frame_hashes": frame_hashes,
            "aggregate_profile": aggregate_profile,
            "frame_count": len(frame_hashes),
            "minimum_match_frames": 3,
            "same_content_threshold": 0.90,
            "possible_match_threshold": 0.76,
        }

        payload = {
            "selected": [
                {
                    "second": item["second"],
                    "score": item["score"],
                    "position": item["position"],
                    "visual_vector": item["visual_vector"],
                    "perceptual_hashes": item.get("perceptual_hashes") or {},
                    "ocr_text": item["ocr_text"],
                }
                for item in selected
            ],
            "scene_changes": list(
                scene_data.get("first_scene_changes") or []
            )[:30],
        }

        signature = (
            hashlib.sha256(
                json.dumps(
                    payload,
                    sort_keys=True,
                    ensure_ascii=False,
                ).encode("utf-8")
            ).hexdigest()
            if selected
            else None
        )

        rejected = [
            item for item in ranked if not item["accepted"]
        ] + duplicate_rejections

        scene_signature = build_scene_signature(
            list(scene_data.get("first_scene_changes") or []),
            duration,
            selected,
        )
        ocr_logo_fusion = fuse_ocr_logo_hints(
            list(ocr_data.get("findings") or []),
            selected,
            duration,
        )
        character_preparation = prepare_anonymous_subjects(selected)
        intro_outro_detection = detect_intro_outro(
            duration,
            selected,
            scene_signature,
            ocr_logo_fusion,
            character_preparation,
        )

        result = {
            "schema_version": 8,
            "state": "completed" if ranked else "no_samples",
            "selection_strategy": "sharpness_content_position_v1",
            "privacy": {
                "mode": "local_only",
                "external_transfer": False,
                "user_approval_required": True,
            },
            "candidate_count": len(ranked),
            "selected_count": len(selected),
            "selected_frames": selected,
            "rejected_frames": rejected,
            "selection_summary": {
                "intro": sum(
                    item["position"] == "intro"
                    for item in selected
                ),
                "content": sum(
                    item["position"] == "content"
                    for item in selected
                ),
                "outro": sum(
                    item["position"] == "outro"
                    for item in selected
                ),
                "duplicate_rejections": len(duplicate_rejections),
            },
            "visual_fingerprint": visual_fingerprint,
            "scene_signature": scene_signature,
            "ocr_logo_fusion": ocr_logo_fusion,
            "character_preparation": character_preparation,
            "intro_outro_detection": intro_outro_detection,
            "visual_signature": signature,
            "signature_algorithm": (
                "sha256-smart-ranked-frame-metadata-v2"
                if signature
                else None
            ),
            "online_ready": bool(selected),
            "external_payload_created": False,
            "comparison_support": {
                "method": "compare_visual_fingerprints",
                "same_content_threshold": 0.90,
                "possible_match_threshold": 0.76,
            },
        }
        result["pipeline_validation"] = validate_visual_pipeline(result)
        return result

    @staticmethod
    def compare(
        first: dict[str, Any] | None,
        second: dict[str, Any] | None,
    ) -> dict[str, Any]:
        return compare_visual_fingerprints(first, second)

    @staticmethod
    def compare_scenes(
        first: dict[str, Any] | None,
        second: dict[str, Any] | None,
    ) -> dict[str, Any]:
        return compare_scene_signatures(first, second)

