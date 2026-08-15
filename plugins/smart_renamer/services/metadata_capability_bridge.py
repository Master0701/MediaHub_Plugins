from __future__ import annotations

class MetadataCapabilityBridge:
    def __init__(self, capability_source=None): self.capability_source=capability_source
    def _provider(self,capability):
        source=self.capability_source
        if source is None:
            return None

        resolve=getattr(source,"resolve",None)
        if callable(resolve):
            try:
                resolved=resolve(capability)
            except Exception:
                resolved=None

            if isinstance(resolved,tuple):
                provider=resolved[-1] if resolved else None
            else:
                provider=resolved

            if provider is not None:
                return provider

        for name in (
            "resolve_capability",
            "get_capability_provider",
            "find_capability_provider",
            "get_plugin_capability",
            "get_capability",
        ):
            fn=getattr(source,name,None)
            if callable(fn):
                try:
                    value=fn(capability)
                except Exception:
                    value=None
                if value is not None:
                    return value

        if isinstance(source,dict):
            return source.get(capability)
        return None
    def status(self):
        return {"read":self._provider("metadata.read") is not None,"review":self._provider("metadata.review") is not None,"write":self._provider("metadata.write") is not None}
    @staticmethod
    def _call(provider,names,payload):
        for name in names:
            fn=getattr(provider,name,None)
            if callable(fn): return dict(fn(dict(payload or {})) or {})
        return {}
    def read(self,payload):
        p=self._provider("metadata.read")
        if p is None: return {"available":False,"metadata":{},"execution_allowed":False}
        result=self._call(p,("read_metadata","read","analyze"),payload)
        return {"available":True,**result,"execution_allowed":False}
    def review(self,payload):
        p=self._provider("metadata.review")
        if p is None: return {"available":False,"changes":[],"execution_allowed":False}
        result=self._call(p,("review_metadata","review","analyze"),payload)
        return {"available":True,**result,"execution_allowed":False,"automatic_apply_allowed":False,"human_confirmation_required":True}
