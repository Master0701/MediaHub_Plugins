from __future__ import annotations

import hashlib
import json
from typing import Any


def build_query_plan(query: dict[str, Any]) -> dict[str, Any]:
    reasoning = dict(query.get("query_reasoning") or {})
    accepted = [dict(item) for item in query.get("search_variants") or [] if isinstance(item, dict) and str(item.get("title") or "").strip()]
    rejected = [dict(item) for item in ((reasoning.get("quality_gate") or {}).get("rejected") or []) if isinstance(item, dict)]
    for index, item in enumerate(accepted):
        item.setdefault("priority", index + 1)
        item.setdefault("accepted", True)
        item.setdefault("fallback", any("Fallback" in str(x) for x in item.get("reasons") or []))
    payload = {"accepted_variants": accepted, "rejected_variants": rejected, "media_type": query.get("media_type"), "year": query.get("year"), "season": query.get("season"), "episodes": query.get("episodes") or []}
    plan_id = hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")).hexdigest()[:16]
    return {"schema_version": 1, "plan_id": plan_id, **payload}


def accepted_variants(query: dict[str, Any]) -> list[dict[str, Any]]:
    plan = query.get("query_plan") or {}
    return [dict(item) for item in plan.get("accepted_variants") or [] if isinstance(item, dict) and item.get("accepted", True) and str(item.get("title") or "").strip()]
