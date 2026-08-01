import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from services.semantic_knowledge_engine import SemanticKnowledgeEngine

SOURCE = {"id": "wiki", "name": "Wikipedia"}

def test_primary_is_character():
    result = SemanticKnowledgeEngine().analyze(
        title="Aquaman",
        text="Aquaman ist ein Superheld der gleichnamigen Comicreihen. Im Dezember 2018 erschien der Film Aquaman.",
        source=SOURCE,
    )
    assert result["primary_entity_type"] == "character"

def test_movie_year_is_2018_not_2017():
    result = SemanticKnowledgeEngine().analyze(
        title="Aquaman",
        text="In Justice League aus dem Jahr 2017 hat Aquaman einen Auftritt. Im Dezember 2018 erschien der Film Aquaman.",
        source=SOURCE,
    )
    movies = [x for x in result["entity_proposals"] if x["entity_type"] == "movie"]
    assert any(x["year"] == 2018 for x in movies)
    assert not any(x["year"] == 2017 for x in movies)

def test_sequel_term():
    result = SemanticKnowledgeEngine().analyze(
        title="Aquaman",
        text="Aquaman and the Lost Kingdom ist die Fortsetzung des Films Aquaman.",
        source=SOURCE,
    )
    assert any(x["relation_type"] == "sequel" for x in result["relation_proposals"])
