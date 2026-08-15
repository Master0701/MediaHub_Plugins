from services.batch_rename_review_provider import BatchRenameReviewProvider

class Single:
    def analyze(self,payload):
        return {"suggested_name":payload.get("proposed_name",""),"confidence":0.0,"warnings":[]}

def p(): return BatchRenameReviewProvider(Single())

def test_metadata_review_episode_title_has_priority():
    r=p().analyze({"items":[{
        "original_name":"12monkeys-s03e02-480p.mkv",
        "metadata_review":{"series_title":"12 Monkeys","episode_title":"Wächter"},
        "metadata_read":{"episode_title":"Alt"},
        "episode_title":"Noch älter",
    }]})
    x=r["items"][0]
    assert x["suggested_name"]=="12 Monkeys - S03E02 - Wächter.mkv"
    assert x["episode_title_source"]=="metadata_review"

def test_nested_nfo_episode_title_is_used():
    r=p().analyze({"items":[{
        "original_name":"12monkeys-s03e03-480p.mkv",
        "metadata_read":{"nfo":{"series_title":"12 Monkeys","episode_title":"Die Wächter"}},
    }]})
    x=r["items"][0]
    assert x["suggested_name"]=="12 Monkeys - S03E03 - Die Wächter.mkv"
    assert x["episode_title_source"]=="metadata_read"

def test_local_review_is_fallback():
    r=p().analyze({"items":[{
        "original_name":"12monkeys-s03e04-480p.mkv",
        "local_review":{"structured_recommendation":{"fields":{"episode_title":"Brüder"},"confidence":0.91}},
    }]})
    x=r["items"][0]
    assert x["suggested_name"]=="12 Monkeys - S03E04 - Brüder.mkv"
    assert x["episode_title_source"]=="local_ai_review"

def test_no_title_remains_clean():
    r=p().analyze({"items":[{"original_name":"12monkeys-s03e05-480p.mkv"}]})
    x=r["items"][0]
    assert x["suggested_name"]=="12 Monkeys - S03E05.mkv"
    assert x["episode_title"]==""
