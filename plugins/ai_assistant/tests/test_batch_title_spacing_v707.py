from services.batch_rename_review_provider import BatchRenameReviewProvider


class Single:
    def analyze(self,payload):
        return {"suggested_name":payload.get("proposed_name",""),"confidence":0.0,"warnings":[]}


def test_glued_number_word_title_is_normalized():
    p=BatchRenameReviewProvider(Single())
    result=p.analyze({
        "items":[{
            "original_name":"12monkeys-s03e01-480p.mkv",
            "source_path":"D:/x/12monkeys-s03e01-480p.mkv",
        }]
    })
    assert result["items"][0]["suggested_name"]=="12 Monkeys - S03E01.mkv"
