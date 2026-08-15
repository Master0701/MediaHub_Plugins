from services.ai_review_comparison import AIReviewComparisonService


def test_name_token_conflict_is_never_reported_as_agreement():
    service=AIReviewComparisonService()
    result=service.compare(
        {
            "original_name":"lim-12monkeys-s03e01-480p.mkv",
            "proposed_name":"12 Monkeys - S03E01.mkv",
            "confidence":0.95,
        },
        {
            "available":True,
            "suggested_name":"12 Monkeys - S02E01.mkv",
            "confidence":0.95,
            "structured_recommendation":{
                "fields":{},
                "suggested_name":"12 Monkeys - S02E01.mkv",
                "confidence":0.95,
            },
        },
    )
    assert result["status"]=="conflict"
    assert result["differences"] >= 1
    assert "season" in result["conflict_fields"]
    assert "Staffel" in result["summary"]


def test_matching_name_tokens_agree_when_no_other_difference():
    service=AIReviewComparisonService()
    result=service.compare(
        {"proposed_name":"12 Monkeys - S03E01.mkv","confidence":0.95},
        {
            "available":True,
            "suggested_name":"12 Monkeys - S03E01.mkv",
            "confidence":0.95,
            "structured_recommendation":{"fields":{},"suggested_name":"12 Monkeys - S03E01.mkv"},
        },
    )
    assert result["status"]=="agree"
