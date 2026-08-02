import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from services.franchise_connection_intelligence import FranchiseConnectionIntelligence

def analyze(text):
    return FranchiseConnectionIntelligence.analyze(main_node={"key":"series:ncis los angeles","node_type":"series","title":"NCIS: Los Angeles"},text=text,source={"id":"test"})

def test_spin_off_crossover_backdoor_and_universe():
    result=analyze("Spin-off von NCIS. Crossover mit Hawaii Five-0. Backdoor-Pilot für NCIS: Hawaiʻi. Spielt im selben Universum wie JAG.")
    types={e["edge_type"] for e in result["edges"]}
    assert {"spin_off_of","crossover_with","backdoor_pilot_for","shares_universe_with"} <= types
    assert all(e["requires_confirmation"] and not e["automatic_import"] for e in result["edges"])

def test_direct_spin_off_wording():
    result=analyze("Direktes Spin-off der Serie NCIS.")
    assert result["edges"][0]["target_node_key"] == "series:ncis"
