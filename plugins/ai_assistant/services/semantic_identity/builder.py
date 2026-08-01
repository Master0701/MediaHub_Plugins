from __future__ import annotations

import re
import unicodedata
from typing import Any

from services.knowledge_learning import KnowledgeLearningService
from services.fingerprint_store import FingerprintReferenceStore
from services.visual_knowledge import VisualKnowledgeStore
from services.semantic_identity.models import IdentityCandidate, IdentityEvidence


def _normalize(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = text.encode("ascii", "ignore").decode("ascii").lower()
    return " ".join(re.findall(r"[a-z0-9]+", text))


def _year(value: Any) -> int | None:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    return number if 1800 <= number <= 2200 else None


class IdentityCandidateBuilder:
    """Sammelt mögliche Medienidentitäten, ohne eine Entscheidung zu treffen."""

    def __init__(self, knowledge_database_path=None):
        self.database_path = knowledge_database_path
        self.knowledge = (
            KnowledgeLearningService(knowledge_database_path)
            if knowledge_database_path is not None
            else None
        )
        self.fingerprint_store = (
            FingerprintReferenceStore(knowledge_database_path)
            if knowledge_database_path is not None
            else None
        )
        self.visual_knowledge = (
            VisualKnowledgeStore(knowledge_database_path)
            if knowledge_database_path is not None
            else None
        )

    @staticmethod
    def _key(title: str, year: int | None, media_type: str) -> tuple[str, int | None, str]:
        return (_normalize(title), year, str(media_type or "other").lower())

    def _add(
        self,
        candidates: dict[tuple[str, int | None, str], IdentityCandidate],
        *,
        title: Any,
        media_type: Any = "other",
        year: Any = None,
        season: Any = None,
        episode: Any = None,
        edition: Any = None,
        original_title: Any = None,
        aliases: list[Any] | None = None,
        external_ids: dict[str, Any] | None = None,
        evidence: IdentityEvidence,
    ) -> None:
        clean_title = str(title or "").strip()
        if len(_normalize(clean_title)) < 3:
            return
        clean_type = str(media_type or "other").strip().lower() or "other"
        clean_year = _year(year)
        key = self._key(clean_title, clean_year, clean_type)
        candidate = candidates.get(key)
        if candidate is None:
            candidate = IdentityCandidate(
                media_type=clean_type,
                title=clean_title,
                year=clean_year,
                season=season,
                episode=episode,
                edition=str(edition).strip() if edition else None,
                original_title=str(original_title).strip() if original_title else None,
                external_ids=dict(external_ids or {}),
            )
            candidates[key] = candidate
        candidate.aliases.update(str(item).strip() for item in (aliases or []) if str(item).strip())
        candidate.evidence.append(evidence)

    @staticmethod
    def _candidate_score(candidate: IdentityCandidate) -> float:
        strongest: dict[str, float] = {}
        for item in candidate.evidence:
            strongest[item.independent_group] = max(
                strongest.get(item.independent_group, 0.0),
                max(0.0, min(1.0, item.confidence)),
            )
        if not strongest:
            return 0.0
        product = 1.0
        for confidence in strongest.values():
            product *= 1.0 - (confidence * 0.72)
        score = 1.0 - product
        if len(strongest) == 1:
            score *= 0.78
        return round(max(0.0, min(1.0, score)), 4)

    def build(self, analysis: dict[str, Any]) -> dict[str, Any]:
        candidates: dict[tuple[str, int | None, str], IdentityCandidate] = {}
        identification = analysis.get("identification") or {}
        filename_title = identification.get("title_candidate")
        if filename_title:
            self._add(
                candidates,
                title=filename_title,
                media_type=identification.get("media_type") or "other",
                year=identification.get("year"),
                season=identification.get("season"),
                edition=identification.get("edition_candidate"),
                evidence=IdentityEvidence(
                    source="filename", value=str(filename_title),
                    confidence=float(identification.get("confidence") or 0.0),
                    detail="Kandidat aus Datei- oder Ordnername.",
                    independent_group="filename",
                ),
            )

        ranking = ((analysis.get("online") or {}).get("ranking") or {})
        for match in ranking.get("matches") or []:
            title = match.get("title") or match.get("original_title")
            if not title:
                continue
            self._add(
                candidates,
                title=title,
                original_title=match.get("original_title"),
                aliases=list(match.get("aliases") or []),
                media_type=match.get("media_type") or match.get("type") or "other",
                year=match.get("year"),
                season=match.get("season"),
                episode=match.get("episode"),
                external_ids=match.get("external_ids") or {},
                evidence=IdentityEvidence(
                    source="online", value=str(title),
                    confidence=float(match.get("score") or 0.0),
                    detail=f"Online-Kandidat von {match.get('provider_name') or match.get('provider_id') or 'Provider'}.",
                    independent_group="online", metadata={"provider_id": match.get("provider_id")},
                ),
            )

        visual = ((analysis.get("in_video") or {}).get("visual_intelligence") or {})
        fusion = visual.get("ocr_logo_fusion") or {}
        for item in fusion.get("candidates") or []:
            if not item.get("title_candidate"):
                continue
            title = str(item.get("text") or "").strip()
            quality = float(item.get("text_quality") or 0.0)
            confidence = min(float(item.get("score") or 0.0), quality)
            if confidence < 0.62:
                continue
            self._add(
                candidates,
                title=title, media_type="other",
                evidence=IdentityEvidence(
                    source="visual_ocr", value=title, confidence=confidence,
                    detail="Titelkarten-Kandidat aus OCR-/Frame-Fusion.",
                    independent_group="visual_text",
                    metadata={"second": item.get("second"), "logo_candidate": bool(item.get("logo_candidate"))},
                ),
            )

        fingerprint_agent = (
            (((analysis.get("in_video") or {}).get("agents") or {})
             .get("fingerprint_agent") or {})
        )
        fingerprint_value = fingerprint_agent.get("video_fingerprint")
        matched = fingerprint_agent.get("matched_identity")
        if not isinstance(matched, dict) and self.fingerprint_store is not None:
            matched = self.fingerprint_store.lookup(fingerprint_value)
        if isinstance(matched, dict) and matched.get("title"):
            self._add(
                candidates,
                title=matched.get("title"),
                media_type=matched.get("media_type") or "other",
                year=matched.get("year"),
                season=matched.get("season"),
                episode=matched.get("episode"),
                edition=matched.get("edition"),
                evidence=IdentityEvidence(
                    source="fingerprint",
                    value=str(matched.get("title")),
                    confidence=float(matched.get("confidence") or 0.99),
                    detail="Exakter Treffer in der lokalen Fingerprint-Referenzdatenbank.",
                    independent_group="fingerprint",
                    metadata={
                        "fingerprint": fingerprint_value,
                        "knowledge_identity_id": matched.get("knowledge_identity_id"),
                    },
                ),
            )

        visual_signature = str(visual.get("visual_signature") or "").strip()
        if visual_signature and self.visual_knowledge is not None and self.knowledge is not None:
            for visual_match in self.visual_knowledge.find_by_signature(visual_signature):
                identity_id = visual_match.get("identity_id")
                learned_items = []
                snapshot = self.knowledge.export_snapshot()
                for learned in snapshot.get("identities") or []:
                    if learned.get("id") == identity_id:
                        learned_items.append(learned)
                for learned in learned_items:
                    self._add(
                        candidates,
                        title=learned.get("canonical_title"),
                        original_title=learned.get("original_title"),
                        media_type=learned.get("media_type") or "other",
                        year=learned.get("release_year"),
                        season=learned.get("season"),
                        episode=learned.get("episode"),
                        edition=learned.get("edition"),
                        external_ids=learned.get("external_ids") or {},
                        evidence=IdentityEvidence(
                            source="visual_knowledge",
                            value=str(learned.get("canonical_title") or ""),
                            confidence=float(visual_match.get("confidence") or 0.95),
                            detail="Exakte visuelle Signatur in bestätigtem Visual Knowledge gefunden.",
                            independent_group="visual",
                            metadata={
                                "identity_id": identity_id,
                                "visual_signature": visual_signature,
                            },
                        ),
                    )

        lookup_terms = []
        if filename_title:
            lookup_terms.append(str(filename_title))
        lookup_terms.extend(
            str(item.get("text") or "")
            for item in (fusion.get("candidates") or [])[:5]
            if item.get("text")
        )
        if self.knowledge is not None:
            seen = set()
            for term in lookup_terms:
                normalized = _normalize(term)
                if not normalized or normalized in seen:
                    continue
                seen.add(normalized)
                for learned in self.knowledge.lookup(term):
                    self._add(
                        candidates,
                        title=learned.get("canonical_title"),
                        original_title=learned.get("original_title"),
                        aliases=list(learned.get("aliases") or []),
                        media_type=learned.get("media_type") or "other", year=learned.get("release_year"),
                        season=learned.get("season"), episode=learned.get("episode"), edition=learned.get("edition"),
                        external_ids=learned.get("external_ids") or {},
                        evidence=IdentityEvidence(
                            source="learned_knowledge", value=term,
                            confidence=float(learned.get("confidence") or 1.0),
                            detail="Lokaler Treffer über bestätigten Titel oder Alias.",
                            independent_group="knowledge", metadata={"identity_id": learned.get("id")},
                        ),
                    )

        output = []
        for candidate in candidates.values():
            item = candidate.to_dict()
            item["candidate_score"] = self._candidate_score(candidate)
            item["candidate_score_percent"] = round(item["candidate_score"] * 100, 1)
            item["stage"] = "candidate"
            output.append(item)
        output.sort(key=lambda item: (item["candidate_score"], item["source_count"]), reverse=True)
        return {
            "schema_version": 1,
            "stage": "candidate_builder",
            "decision_made": False,
            "candidate_count": len(output),
            "candidates": output,
            "best_candidate": output[0] if output else None,
            "sources_considered": ["filename", "online", "visual_ocr", "fingerprint", "visual_knowledge", "learned_knowledge"],
            "limitations": [
                "Die Evidence Bridge übernimmt nur identitätsgebundene Treffer; rohe Fingerprints oder beliebige Bildmerkmale erhöhen die Sicherheit nicht.",
                "Audio- und objektbasierte Bildmodelle werden in späteren Semantic-Identity-Stufen ergänzt.",
            ],
        }
