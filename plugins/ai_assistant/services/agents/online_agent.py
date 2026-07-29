from __future__ import annotations

from typing import Any

from services.online_result_ranker import OnlineResultRanker
from services.query_plan import accepted_variants, build_query_plan


class OnlineAgent:
    """Führt geeignete Quellen aus und vereinheitlicht deren Ergebnisse."""

    def __init__(self, source_manager):
        self.source_manager = source_manager
        self.ranker = OnlineResultRanker()

    def run(
        self,
        analysis: dict,
    ) -> dict:
        source_plan = analysis.get("source_plan") or {}
        planned_query = source_plan.get("query")

        query = dict(planned_query) if isinstance(planned_query, dict) else self.source_manager.build_query(analysis)
        if not isinstance(query.get("query_plan"), dict):
            query["query_plan"] = build_query_plan(query)
        accepted = accepted_variants(query)
        query["search_variants"] = accepted
        if not accepted:
            return {
                "schema_version": 4, "executed": False,
                "reason": "Der zentrale QueryPlan enthält keine freigegebenen Suchvarianten.",
                "query": query, "provider_results": [],
                "ranking": {"schema_version": 4, "matches": [], "best_match": None, "match_count": 0, "confidence": 0.0, "confidence_gap": None, "decision": "not_executed", "weights": dict(self.ranker.WEIGHTS)},
                "successful_sources": 0, "failed_sources": 0,
                "search_variant_count": 0, "executed_queries": 0,
            }

        provider_results = self.source_manager.execute(
            query
        )
        ranking = self.ranker.rank(
            query,
            provider_results,
        )

        return {
            "schema_version": 3,
            "executed": True,
            "query": query,
            "provider_results": provider_results,
            "ranking": ranking,
            "successful_sources": sum(
                1
                for item in provider_results
                if item.get("status")
                in {"ok", "success", "ready"}
            ),
            "failed_sources": sum(
                1
                for item in provider_results
                if item.get("status")
                in {"error", "failed"}
            ),
            "search_variant_count": len(
                query.get("search_variants") or []
            ),
            "executed_queries": sum(
                len(item.get("queries") or [])
                for item in provider_results
            ),
        }
