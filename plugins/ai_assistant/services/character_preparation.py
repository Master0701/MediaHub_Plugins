from __future__ import annotations

from typing import Any

from services.visual_fingerprint import similarity


def prepare_anonymous_subjects(
    selected_frames: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    """Gruppiert wiederkehrende Zentralmotive anonym.

    Dies ist ausdrücklich keine Gesichtserkennung und keine biometrische
    Identifikation. Es werden nur lokale perceptuelle Hashes des zentralen
    Bildbereichs verglichen.
    """
    frames = []
    for item in selected_frames or []:
        hashes = dict(item.get("perceptual_hashes") or {})
        center_hash = hashes.get("center_dhash")
        if not center_hash:
            continue
        frames.append(
            {
                "second": round(float(item.get("second") or 0.0), 2),
                "position": str(item.get("position") or "unknown"),
                "score": round(float(item.get("score") or 0.0), 4),
                "center_dhash": str(center_hash),
            }
        )

    groups: list[dict[str, Any]] = []

    for frame in frames:
        best_group = None
        best_similarity = 0.0

        for group in groups:
            score = similarity(
                frame["center_dhash"],
                group["representative_center_dhash"],
            )
            if score > best_similarity:
                best_similarity = score
                best_group = group

        if best_group is not None and best_similarity >= 0.86:
            best_group["occurrences"].append(
                {
                    "second": frame["second"],
                    "position": frame["position"],
                    "score": frame["score"],
                    "similarity_to_representative": best_similarity,
                }
            )
            best_group["max_similarity"] = max(
                float(best_group.get("max_similarity") or 0.0),
                best_similarity,
            )
        else:
            groups.append(
                {
                    "anonymous_subject_id": f"subject-{len(groups) + 1:03d}",
                    "representative_center_dhash": frame["center_dhash"],
                    "occurrences": [
                        {
                            "second": frame["second"],
                            "position": frame["position"],
                            "score": frame["score"],
                            "similarity_to_representative": 1.0,
                        }
                    ],
                    "max_similarity": 1.0,
                }
            )

    for group in groups:
        occurrences = list(group.get("occurrences") or [])
        group["occurrence_count"] = len(occurrences)
        group["recurring"] = len(occurrences) >= 2
        group["positions"] = sorted(
            {
                str(item.get("position") or "unknown")
                for item in occurrences
            }
        )
        group["importance_score"] = round(
            min(
                1.0,
                (len(occurrences) / 4.0)
                + (
                    sum(float(item.get("score") or 0.0) for item in occurrences)
                    / max(len(occurrences), 1)
                )
                * 0.35,
            ),
            4,
        )

    groups.sort(
        key=lambda item: (
            bool(item.get("recurring")),
            float(item.get("importance_score") or 0.0),
            int(item.get("occurrence_count") or 0),
        ),
        reverse=True,
    )

    return {
        "schema_version": 1,
        "state": "completed" if frames else "no_candidates",
        "method": "anonymous_center_visual_grouping_v1",
        "face_detection": False,
        "biometric_identification": False,
        "name_assignment": False,
        "candidate_frame_count": len(frames),
        "anonymous_subject_count": len(groups),
        "recurring_subject_count": sum(
            bool(group.get("recurring")) for group in groups
        ),
        "subjects": groups[:20],
        "limitations": [
            "Ein Zentralmotiv kann eine Person, mehrere Personen oder ein anderes Objekt sein.",
            "Es werden keine Gesichter, Schauspieler oder Charaktere benannt.",
            "Die Gruppierung dient nur als lokale Vorbereitung für spätere optionale Modelle.",
        ],
        "privacy": {
            "mode": "local_only",
            "external_transfer": False,
            "biometric_data_created": False,
        },
    }
