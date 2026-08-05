from __future__ import annotations

import re
from typing import Any


class EntityProposalQualityFilter:
    STRATEGY = "entity_proposal_quality_filter_v705"

    SENTENCE_FRAGMENT_MARKERS = (
        " dass ",
        " nachdem ",
        " während ",
        " obwohl ",
        " sodass ",
        " um ",
        " zu ",
        " und ",
        " die ",
        " der ",
        " dem ",
        " den ",
        " ein ",
        " eine ",
        " ist ",
        " hat ",
        " wurde ",
        " werden ",
    )

    VERB_MARKERS = {
        "befreit",
        "sucht",
        "findet",
        "arbeitet",
        "rettet",
        "entführt",
        "kämpft",
        "tötet",
        "trifft",
        "geht",
        "kommt",
        "erfährt",
        "beschließt",
        "verwendet",
        "wirft",
        "greift",
        "liegt",
        "macht",
    }

    ALLOWED_LONG_TYPES = {
        "artifact",
        "location",
        "organization",
        "franchise",
        "universe",
        "timeline",
    }

    @staticmethod
    def _norm(value: Any) -> str:
        return " ".join(str(value or "").strip().split())

    @classmethod
    def _quality_reasons(
        cls,
        proposal: dict[str, Any],
    ) -> list[str]:
        reasons = []
        node_type = cls._norm(proposal.get("node_type")).casefold()
        title = cls._norm(proposal.get("title"))
        node_key = cls._norm(proposal.get("node_key"))
        text = title.casefold()

        words = re.findall(r"[A-Za-zÄÖÜäöüß0-9']+", title)
        word_count = len(words)

        if not title or not node_key:
            reasons.append("missing_identity_fields")
            return reasons

        if word_count > 6 and node_type not in cls.ALLOWED_LONG_TYPES:
            reasons.append("too_many_words_for_entity")

        if len(title) > 64 and node_type not in cls.ALLOWED_LONG_TYPES:
            reasons.append("title_too_long")

        if "." in title or "," in title or ";" in title:
            reasons.append("contains_sentence_punctuation")

        if node_type == "character":
            if words and words[0].casefold() in cls.VERB_MARKERS:
                reasons.append("starts_with_verb")

            if any(
                marker in f" {text} "
                for marker in cls.SENTENCE_FRAGMENT_MARKERS
            ) and word_count >= 4:
                reasons.append("looks_like_sentence_fragment")

            lower_words = {word.casefold() for word in words}
            if lower_words & cls.VERB_MARKERS:
                reasons.append("contains_action_verb")

            if word_count == 1 and words[0].casefold() in {
                "ist", "hat", "er", "sie", "und", "dass"
            }:
                reasons.append("invalid_single_token_character")

        if node_type == "artifact" and word_count > 5:
            reasons.append("artifact_name_too_long")

        return sorted(set(reasons))

    @classmethod
    def build(
        cls,
        *,
        missing_entity_resolution: dict[str, Any],
        source: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        proposals = list(
            missing_entity_resolution.get(
                "missing_node_proposals"
            ) or []
        )

        accepted = []
        rejected = []

        for proposal in proposals:
            if not isinstance(proposal, dict):
                continue

            reasons = cls._quality_reasons(proposal)
            enriched = dict(proposal)

            if reasons:
                enriched["quality_status"] = "rejected"
                enriched["quality_reasons"] = reasons
                enriched["automatic_creation"] = False
                enriched["requires_confirmation"] = True
                rejected.append(enriched)
            else:
                enriched["quality_status"] = "accepted_for_review"
                enriched["quality_reasons"] = []
                enriched["automatic_creation"] = False
                enriched["requires_confirmation"] = True
                accepted.append(enriched)

        return {
            "schema_version": 1,
            "strategy": cls.STRATEGY,
            "source": {
                "id": (source or {}).get("id"),
                "url": (source or {}).get("url"),
                "name": (source or {}).get("name"),
            },
            "accepted_proposals": accepted,
            "rejected_proposals": rejected,
            "summary": {
                "input_proposal_count": len(proposals),
                "accepted_proposal_count": len(accepted),
                "rejected_proposal_count": len(rejected),
                "rejection_rate": (
                    round(len(rejected) / len(proposals), 4)
                    if proposals else 0.0
                ),
            },
            "decision": {
                "status": (
                    "needs_confirmation"
                    if accepted else "no_safe_proposals"
                ),
                "automatic_creation": False,
            },
            "automatic_import": False,
            "requires_confirmation": True,
        }
