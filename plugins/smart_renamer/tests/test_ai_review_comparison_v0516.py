from services.ai_review_comparison import AIReviewComparisonService


def test_comparison_marks_field_differences():
    result=AIReviewComparisonService().compare(
        {
            "media_type":"movie",
            "title":"Batman",
            "year":"1989",
            "confidence":0.82,
        },
        {
            "available":True,
            "confidence":0.91,
            "structured_recommendation":{
                "candidate_id":"movie-2022",
                "candidate_valid":True,
                "fields":{
                    "media_type":"movie",
                    "title":"The Batman",
                    "year":"2022",
                },
                "confidence":0.91,
                "rationale":"Andere Fassung erkannt.",
            },
        },
    )
    assert result["status"]=="different"
    assert result["differences"]==2
    changed={x["field"] for x in result["fields"] if x["different"]}
    assert changed=={"title","year"}
    assert result["execution_allowed"] is False
    assert result["automatic_apply_allowed"] is False


def test_comparison_reports_agreement():
    result=AIReviewComparisonService().compare(
        {"media_type":"series","season":"01","episode":"02","confidence":0.80},
        {
            "available":True,
            "structured_recommendation":{
                "candidate_id":"series-primary",
                "candidate_valid":True,
                "fields":{"media_type":"series","season":"01","episode":"02"},
                "confidence":0.87,
            },
        },
    )
    assert result["status"]=="agree"
    assert result["differences"]==0


def test_no_ai_is_explicit():
    result=AIReviewComparisonService().compare(
        {"title":"Batman","confidence":0.7},
        {"available":False},
    )
    assert result["status"]=="no_ai"
    assert "Kein KI-Provider" in result["summary"]


def test_text_formatter_shows_local_ai_and_lock():
    service=AIReviewComparisonService()
    result=service.compare(
        {"title":"Batman","year":"1989","confidence":0.8},
        {
            "available":True,
            "structured_recommendation":{
                "candidate_id":"c1",
                "candidate_valid":True,
                "fields":{"title":"The Batman","year":"2022"},
                "confidence":0.9,
                "rationale":"Test",
            },
        },
    )
    text=service.format_text(result)
    assert "Lokale Erkennung ↔ KI-Empfehlung" in text
    assert "Batman ≠ The Batman" in text
    assert "1989 ≠ 2022" in text
    assert "keine automatische Übernahme" in text
