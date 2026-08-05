from services.backend_registry import RenamerBackendRegistry
def test_backend_order_and_fallback(tmp_path):
 r=RenamerBackendRegistry(tmp_path); assert [x["backend_id"] for x in r.describe_backends()]==["mediahub_native","renamer_windows"]; assert r.get_capability_status()["active_preview_backend_id"]=="mediahub_native"
