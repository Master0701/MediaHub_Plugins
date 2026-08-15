from services.batch_rename_review_provider import BatchRenameReviewProvider

class Single:
    def analyze(self,payload):
        return {"suggested_name":payload.get("proposed_name",""),"confidence":0.0,"warnings":[]}

def p(): return BatchRenameReviewProvider(Single())

def test_diagnostics_show_metadata_and_nested_nfo():
    r=p().analyze({"items":[{
        "original_name":"12monkeys-s04e05.mkv",
        "metadata_read":{"nfo":{"episode_title":"Masks"}},
        "metadata_review":{"series_title":"12 Monkeys"},
    }]})
    d=r["items"][0]["metadata_diagnostics"]
    assert d["metadata_read_present"] is True
    assert d["metadata_review_present"] is True
    assert d["nfo_present"] is True
    assert "Masks" in d["episode_title_values_read"]

def test_diagnostics_show_no_episode_title_values():
    r=p().analyze({"items":[{
        "original_name":"12monkeys-s04e05.mkv",
        "metadata_read":{"series_title":"12 Monkeys"},
    }]})
    d=r["items"][0]["metadata_diagnostics"]
    assert d["metadata_read_present"] is True
    assert d["episode_title_field_count"]==0
