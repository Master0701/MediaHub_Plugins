from services.batch_rename_review_provider import BatchRenameReviewProvider


class Single:
    def analyze(self,payload):
        return {"suggested_name":payload.get("proposed_name",""),"confidence":0.0,"warnings":[]}


def test_online_title_is_used_only_after_local_sources_are_empty():
    def online(query):
        assert query["title"]=="12 Monkeys"
        assert query["season"]==3
        assert query["episode"]==2
        return {
            "available":True,
            "accepted":True,
            "episode_title":"Wächter",
            "confidence":0.93,
            "sources":["tmdb","tvdb"],
        }

    p=BatchRenameReviewProvider(Single(), online)
    r=p.analyze({
        "reference":{"proposed_name":"12 Monkeys - S03E01.mkv","media_type":"series"},
        "items":[{
            "original_name":"lim-12monkeys-s03e02-480p.mkv",
            "metadata_read":{"episode_title":"Ohne Titel"},
        }],
    })
    x=r["items"][0]
    assert x["suggested_name"]=="12 Monkeys - S03E02 - Wächter.mkv"
    assert x["episode_title_source"]=="online_fusion"
    assert x["episode_title_online"]["accepted"] is True


def test_real_metadata_title_still_beats_online():
    calls=[]
    def online(query):
        calls.append(query)
        return {
            "available":True,
            "accepted":True,
            "episode_title":"Online",
            "confidence":0.99,
        }

    p=BatchRenameReviewProvider(Single(), online)
    r=p.analyze({"items":[{
        "original_name":"12monkeys-s03e02.mkv",
        "metadata_review":{"episode_title":"Lokal"},
    }]})
    x=r["items"][0]
    assert x["suggested_name"]=="12 Monkeys - S03E02 - Lokal.mkv"
    assert x["episode_title_source"]=="metadata_review"
    assert calls==[]
