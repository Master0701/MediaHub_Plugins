from pathlib import Path
import sys

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
if str(PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT))

from services.media_analyzer import MediaAnalyzer


def test_cached_online_result_survives_reasoning_refresh():
    analyzer = MediaAnalyzer.__new__(MediaAnalyzer)

    class DummySourceManager:
        def plan(self, result):
            return {
                "candidate_sources": [],
                "executed": False,
                "query": {},
            }

    class DummySupervisor:
        def evaluate(self, result):
            return {
                "next_steps": [],
            }

    class DummyCandidateBuilder:
        def build(self, result):
            return []

    class DummyEvidenceCollector:
        def collect(self, candidates, result):
            return []

    class DummyContradictionDetector:
        def detect(self, evidence, result):
            return []

    class DummyConfidenceCalculator:
        def calculate(self, contradictions, result):
            return {}

    class DummyDecisionExplainer:
        def explain(self, confidence, result):
            return {}

    class DummySemanticEngine:
        def finalize(self, explanation, result):
            return {
                "final_status": "confirmed",
            }

    class DummyDecisionEngine:
        def evaluate(self, result):
            return {}

    class DummyDecisionPlanner:
        def build(self, result):
            return {}

    analyzer.source_manager = DummySourceManager()
    analyzer.supervisor = DummySupervisor()
    analyzer.online_agent = None
    analyzer.cache = None

    analyzer.identity_candidate_builder = DummyCandidateBuilder()
    analyzer.identity_evidence_collector = DummyEvidenceCollector()
    analyzer.identity_contradiction_detector = DummyContradictionDetector()
    analyzer.identity_confidence_calculator = DummyConfidenceCalculator()
    analyzer.identity_decision_explainer = DummyDecisionExplainer()
    analyzer.semantic_identity_engine = DummySemanticEngine()
    analyzer.decision_engine = DummyDecisionEngine()
    analyzer.decision_planner = DummyDecisionPlanner()

    analyzer._build_evidence = lambda result: []

    cached = {
        "identification": {
            "title": "12 Monkeys",
            "year": 1995,
            "media_type": "movie",
        },
        "semantic_identity": {
            "final_status": "confirmed",
        },
        "online": {
            "schema_version": 4,
            "executed": True,
            "provider_results": [
                {
                    "provider": "tmdb",
                    "status": "ok",
                    "matches": [
                        {
                            "title": "12 Monkeys",
                            "year": 1995,
                            "release_date": "1995-12-29",
                            "published_at": "1995-12-29",
                            "media_type": "movie",
                        }
                    ],
                }
            ],
            "ranking": {
                "best_match": {
                    "title": "12 Monkeys",
                    "year": 1995,
                    "release_date": "1995-12-29",
                    "published_at": "1995-12-29",
                    "media_type": "movie",
                }
            },
        },
    }

    result = analyzer._refresh_cached_reasoning(
        Path("12.Monkeys.1995.mkv"),
        cached,
    )

    assert result["online"]["executed"] is True

    best = result["online"]["ranking"]["best_match"]

    assert best["title"] == "12 Monkeys"
    assert best["year"] == 1995
    assert best["release_date"] == "1995-12-29"
    assert best["published_at"] == "1995-12-29"
