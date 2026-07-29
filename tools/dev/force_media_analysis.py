import json
import sys
from pathlib import Path

PLUGIN_DIR = Path(r"D:\eigenes program\MediaHub-Plugins\plugins\ai_assistant")
VIDEO = Path(r"D:\eigenes program\pso-aqua2-ts-1080p.mkv")

if str(PLUGIN_DIR) not in sys.path:
    sys.path.insert(0, str(PLUGIN_DIR))

from plugin import MediaHubAIAssistantPlugin

plugin = MediaHubAIAssistantPlugin(PLUGIN_DIR)

print("Analyse wird vollständig neu ausgeführt ...")
analysis = plugin.analyze_media_file(VIDEO, force=True)

print("\nOberste Schlüssel:")
print(sorted(analysis.keys()))

orchestration = analysis.get("orchestration") or {}
plan = orchestration.get("plan") or {}

print("\nOrchestrator-Schritte:")
for step in plan.get("steps") or []:
    print(
        step.get("id"),
        "state =", step.get("state"),
        "reason =", step.get("reason"),
        "error =", step.get("error"),
    )

fingerprint = (
    (((analysis.get("in_video") or {}).get("agents") or {})
     .get("fingerprint_agent") or {})
    .get("video_fingerprint")
)

print("\nIn-Video-Status:", (analysis.get("in_video") or {}).get("state"))
print("Fingerprint:", fingerprint)

Path("TEST_KI_FORCE_ANALYSE_AUSGABE.json").write_text(
    json.dumps(analysis, indent=2, ensure_ascii=False),
    encoding="utf-8",
)
