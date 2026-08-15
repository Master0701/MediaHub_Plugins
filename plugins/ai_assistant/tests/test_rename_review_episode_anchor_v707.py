from services.rename_review_provider import RenameReviewProvider


def test_filename_episode_anchor_overrides_conflicting_candidate():
    provider=RenameReviewProvider()
    result=provider.analyze({
        "current_name":"lim-12monkeys-s03e01-480p.mkv",
        "proposed_name":"12 Monkeys - S03E01.mkv",
        "renamer":{"season":"3","episode":"1","confidence":0.95},
        "candidates":[{
            "candidate_id":"wrong",
            "season":"2",
            "episode":"1",
            "confidence":0.99,
        }],
    })
    fields=result["structured_recommendation"]["fields"]
    assert fields["season"]=="3"
    assert fields["episode"]=="1"
    assert result["suggested_name"]=="12 Monkeys - S03E01.mkv"
    assert result["recommendation"]=="review_conflict"
    assert result["conflicts"][0]["field"]=="season"


def test_non_conflicting_candidate_keeps_anchor_without_conflict():
    provider=RenameReviewProvider()
    result=provider.analyze({
        "current_name":"show-s03e01.mkv",
        "proposed_name":"Show - S03E01.mkv",
        "renamer":{"season":"3","episode":"1","confidence":0.95},
        "candidates":[{
            "candidate_id":"ok",
            "season":"3",
            "episode":"1",
            "confidence":0.97,
        }],
    })
    assert result["structured_recommendation"]["fields"]["season"]=="3"
    assert result["conflicts"]==[]
