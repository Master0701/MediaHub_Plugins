from services.batch_rename_review_provider import BatchRenameReviewProvider

class Single:
    def analyze(self,payload):
        return {"suggested_name":payload.get("proposed_name",""),"confidence":0.0,"warnings":[]}

def test_reference_title_without_space_is_normalized():
    p=BatchRenameReviewProvider(Single())
    r=p.analyze({
        "reference":{"proposed_name":"12monkeys - S03E02.mkv","media_type":"series"},
        "items":[{"original_name":"lim-12monkeys-s03e01-480p.mkv","source_path":"D:/x/lim-12monkeys-s03e01-480p.mkv"}],
    })
    assert r["items"][0]["suggested_name"]=="12 Monkeys - S03E01.mkv"

def test_metadata_title_without_space_is_normalized():
    p=BatchRenameReviewProvider(Single())
    r=p.analyze({"items":[{
        "original_name":"lim-12monkeys-s03e01-480p.mkv",
        "metadata_read":{"series_title":"12monkeys"},
    }]})
    assert r["items"][0]["suggested_name"]=="12 Monkeys - S03E01.mkv"
