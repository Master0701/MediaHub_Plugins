from services.input_quality import evaluate_text


def test_ocr_rejects_fragment_heavy_noise():
    text = (
        'ET id ur eo 123 5 in ail we a un MAD 7D '
        'vr ir N owl ts ei ss ET un i y Pare yt '
        'BR N UN u ct s aa Be Re st Non te'
    )

    result = evaluate_text(
        text,
        source="ocr",
    )

    assert result.accepted is False


def test_ocr_accepts_normal_title_text():
    result = evaluate_text(
        "Starship Troopers 3",
        source="ocr",
    )

    assert result.accepted is True


def test_ocr_accepts_short_clean_title():
    result = evaluate_text(
        "Chappie",
        source="ocr",
    )

    assert result.accepted is True


def test_filename_rules_are_not_tightened():
    result = evaluate_text(
        "pso aqua2 ts",
        source="filename",
    )

    assert result.accepted is True
