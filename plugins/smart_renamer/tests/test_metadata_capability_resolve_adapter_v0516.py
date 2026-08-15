from services.metadata_capability_bridge import MetadataCapabilityBridge

class MetadataProvider:
    def read_metadata(self,payload=None):
        return {"available":True,"episode_title":"Wächter"}

    def review_metadata(self,payload=None):
        return {"available":True,"change_count":0}

class ResolveTupleRegistry:
    def __init__(self,p): self.p=p
    def resolve(self,capability):
        if capability in ("metadata.read","metadata.review"):
            return ("mediahub.metadata_editor",self.p)
        return (None,None)

class ResolveDirectRegistry:
    def __init__(self,p): self.p=p
    def resolve(self,capability):
        if capability in ("metadata.read","metadata.review"):
            return self.p
        return None

def test_tuple_resolve():
    b=MetadataCapabilityBridge(ResolveTupleRegistry(MetadataProvider()))
    s=b.status()
    assert s["read"] is True
    assert s["review"] is True
    assert s["write"] is False

def test_direct_resolve():
    b=MetadataCapabilityBridge(ResolveDirectRegistry(MetadataProvider()))
    assert b.status()["read"] is True
    assert b.status()["review"] is True
