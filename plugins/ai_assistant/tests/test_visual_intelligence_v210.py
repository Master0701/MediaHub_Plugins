import sys
from pathlib import Path
PLUGIN_DIR=Path(__file__).resolve().parents[1]
if str(PLUGIN_DIR) not in sys.path: sys.path.insert(0,str(PLUGIN_DIR))
from services.visual_intelligence import VisualIntelligenceEngine

def test_ranks_and_filters_frames():
 data={"agents":{"frame_agent":{"samples":[{"second":5,"metrics":{"yavg":120,"ymin":20,"ymax":220,"satavg":12}},{"second":10,"metrics":{"yavg":2,"ymin":0,"ymax":5,"satavg":0}},{"second":15,"metrics":{"yavg":121,"ymin":21,"ymax":221,"satavg":12}}]},"ocr_agent":{"findings":[{"second":5,"text":"STAR TREK"}]},"scene_agent":{"first_scene_changes":[5,15]}}}
 r=VisualIntelligenceEngine().analyze(data,1000)
 assert r["state"]=="completed"
 assert r["selected_count"]==1
 assert r["visual_signature"]
 assert r["privacy"]["external_transfer"] is False

def test_no_samples_is_safe():
 r=VisualIntelligenceEngine().analyze({"agents":{}},0)
 assert r["state"]=="no_samples" and r["visual_signature"] is None
