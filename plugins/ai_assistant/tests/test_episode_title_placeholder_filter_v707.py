from services.batch_rename_review_provider import BatchRenameReviewProvider

class Single:
    def analyze(self,payload):
        return {
            "suggested_name": payload.get("proposed_name",""),
            "confidence": 0.0,
            "warnings": [],
        }

def p():
    return BatchRenameReviewProvider(Single())

def test_ohne_titel_is_not_used_as_episode_title():
    r=p().analyze({"items":[{
        "original_name":"lim-12monkeys-s03e01-480p.mkv",
        "metadata_review":{"series_title":"12 Monkeys","episode_title":"Ohne Titel"},
        "metadata_read":{"nfo":{"episode_title":"Ohne Titel"}},
    }]})
    x=r["items"][0]
    assert x["suggested_name"]=="12 Monkeys - S03E01.mkv"
    assert x["episode_title"]==""
    assert x["metadata_diagnostics"]["episode_title_field_count"]==0
    assert "Ohne Titel" in x["metadata_diagnostics"]["ignored_episode_title_placeholders"]
    assert any("Platzhalter" in w for w in x["warnings"])

def test_unknown_and_untitled_are_rejected():
    for placeholder in ("Unknown","Untitled","Unbekannt","N/A","-"):
        r=p().analyze({"items":[{
            "original_name":"12monkeys-s03e02.mkv",
            "metadata_review":{"episode_title":placeholder},
        }]})
        x=r["items"][0]
        assert x["episode_title"]==""
        assert x["suggested_name"]=="12 Monkeys - S03E02.mkv"

def test_real_episode_title_still_wins():
    r=p().analyze({"items":[{
        "original_name":"12monkeys-s03e03.mkv",
        "metadata_review":{"series_title":"12 Monkeys","episode_title":"Die Wächter"},
        "metadata_read":{"episode_title":"Ohne Titel"},
    }]})
    x=r["items"][0]
    assert x["episode_title"]=="Die Wächter"
    assert x["suggested_name"]=="12 Monkeys - S03E03 - Die Wächter.mkv"
    assert x["episode_title_source"]=="metadata_review"
