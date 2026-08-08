from __future__ import annotations
from typing import Any

class AIReviewBridge:
    CAPABILITY="ai.rename_review"
    def __init__(self, capability_provider=None): self.capability_provider=capability_provider
    def _handler(self):
        p=self.capability_provider
        if p is None: return None
        if callable(p):
            v=p(self.CAPABILITY); return v if callable(v) else None
        g=getattr(p,"get_capability",None)
        if callable(g):
            v=g(self.CAPABILITY); return v if callable(v) else None
        if isinstance(p,dict):
            v=p.get(self.CAPABILITY); return v if callable(v) else None
        return None
    def available(self)->bool: return self._handler() is not None
    def analyze(self,payload:dict[str,Any])->dict[str,Any]:
        h=self._handler()
        if h is None:
            return {"available":False,"provider":"","recommendation":"","confidence":0.0,"rationale":"","requires_human_confirmation":True}
        r=h(dict(payload or {})) or {}
        return {"available":True,"provider":str(r.get("provider") or "configured"),"recommendation":str(r.get("recommendation") or ""),"confidence":float(r.get("confidence") or 0),"rationale":str(r.get("rationale") or ""),"requires_human_confirmation":True}
