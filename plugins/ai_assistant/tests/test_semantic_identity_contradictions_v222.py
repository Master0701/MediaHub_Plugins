import sys
from pathlib import Path
PLUGIN_DIR=Path(__file__).resolve().parents[1]
if str(PLUGIN_DIR) not in sys.path:sys.path.insert(0,str(PLUGIN_DIR))
from services.semantic_identity import IdentityContradictionDetector

def _result(candidates):return {"stage":"evidence_collector","decision_made":False,"candidate_count":len(candidates),"candidates":candidates}
def _candidate(title,year=2023,evidence_strength=0.8,evidence=None):return {"title":title,"media_type":"movie","year":year,"candidate_score":evidence_strength,"evidence_strength":evidence_strength,"evidence":evidence or []}

def test_detects_title_and_year_conflicts():
 r=IdentityContradictionDetector().detect(_result([_candidate("Aquaman and the Lost Kingdom",2023,evidence=[{"source":"online","independent_group":"online","confidence":0.9,"weighted_strength":0.7,"value":"Star Trek","metadata":{"title":"Star Trek","year":2009}}])]))
 kinds={x["kind"] for x in r["best_candidate"]["contradiction_summary"]["conflicts"]}
 assert r["stage"]=="contradiction_detector" and r["decision_made"] is False
 assert "title" in kinds and "year" in kinds

def test_fingerprint_identity_conflict_is_critical():
 r=IdentityContradictionDetector().detect(_result([_candidate("Aquaman and the Lost Kingdom",evidence=[{"source":"fingerprint","independent_group":"fingerprint","confidence":0.99,"weighted_strength":0.95,"value":"The Matrix","metadata":{"title":"The Matrix"}}])]))
 c=r["best_candidate"]["contradiction_summary"]["conflicts"][0]
 assert c["kind"]=="fingerprint_identity" and c["severity"]=="critical" and c["penalty"]>=0.30

def test_compatible_series_episode_types_are_not_conflict():
 r=IdentityContradictionDetector().detect(_result([{"title":"Star Trek","media_type":"series","year":1966,"candidate_score":0.7,"evidence_strength":0.7,"evidence":[{"source":"online","independent_group":"online","confidence":0.8,"weighted_strength":0.6,"value":"Star Trek","metadata":{"title":"Star Trek","media_type":"episode"}}]}]))
 assert "media_type" not in {x["kind"] for x in r["best_candidate"]["contradiction_summary"]["conflicts"]}

def test_near_equal_different_candidates_are_marked_competing():
 r=IdentityContradictionDetector().detect(_result([_candidate("Aquaman",evidence_strength=0.81),_candidate("Star Trek",evidence_strength=0.78)]))
 assert len(r["cross_candidate_conflicts"])==1 and r["cross_candidate_conflicts"][0]["kind"]=="competing_candidates"
