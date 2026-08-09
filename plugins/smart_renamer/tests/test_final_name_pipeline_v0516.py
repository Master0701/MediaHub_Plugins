from pathlib import Path
from services.rule_engine import RenameRuleEngine
from services.rule_pipeline import order_rules_for_final_name

ROOT=Path(__file__).resolve().parents[1]

def apply(name,rules,metadata=None):
    return RenameRuleEngine().apply(name,rules,metadata=metadata or {})["proposed_name"]

def plex_schema():
    return {
        "type":"schema",
        "template":"[titel] - S[staffel]E[episode] - [episodentitel]",
        "label":"Plex-Serienschema",
        "source":"Profil",
        "enabled":True,
        "media_types":["series"],
    }

META={
    "media_type":"series",
    "titel":"12monkeys",
    "staffel":2,
    "episode":1,
    "episodentitel":"sd",
}

NAME="lim-12monkeys-s02e01-sd.mkv"

def test_exact_filename_minus_sd_after_plex():
    rules=[
        plex_schema(),
        {"type":"remove_before_extension","value":"-sd","source":"Benutzer","enabled":True},
    ]
    assert apply(NAME,rules,META)=="12monkeys - S02E01.mkv"

def test_exact_filename_minus_space_sd_after_plex():
    rules=[
        plex_schema(),
        {"type":"remove_before_extension","value":"- sd","source":"Benutzer","enabled":True},
    ]
    assert apply(NAME,rules,META)=="12monkeys - S02E01.mkv"

def test_accidentally_green_cleanup_still_runs_after_profile_schema():
    rules=[
        {"type":"remove_before_extension","value":"-sd","source":"Profil","enabled":True},
        plex_schema(),
    ]
    assert apply(NAME,rules,META)=="12monkeys - S02E01.mkv"

def test_profile_schema_is_always_first():
    rules=[
        {"type":"remove_before_extension","value":"-sd","source":"Profil"},
        {"type":"remove_start","count":3,"source":"Benutzer"},
        plex_schema(),
    ]
    ordered=order_rules_for_final_name(rules)
    assert ordered[0]["type"]=="schema"
    assert ordered[1]["type"]=="remove_before_extension"
    assert ordered[2]["source"]=="Benutzer"

def test_multiple_user_rules_apply_to_profile_result():
    rules=[
        {"type":"remove_start","count":3,"source":"Benutzer","enabled":True},
        plex_schema(),
        {"type":"remove_before_extension","value":"-sd","source":"Benutzer","enabled":True},
    ]
    meta=dict(META)
    meta["titel"]="ABC12monkeys"
    assert apply(NAME,rules,meta)=="12monkeys - S02E01.mkv"

def test_suffix_variants_without_schema():
    for filename in ("show-sd.mkv","show- sd.mkv","show -sd.mkv","show - sd.mkv"):
        assert apply(
            filename,
            [{"type":"remove_before_extension","value":"-sd","source":"Benutzer"}],
        )=="show.mkv"

def test_desktop_clones_profile_rule_to_user():
    text=(ROOT/"plugin.py").read_text(encoding="utf-8")
    assert 'original_source in ("profil","profile")' in text
    assert 'clone["source"]="Benutzer"' in text
    assert "Profilregel = grün" in text

def test_live_preview_stays_fast():
    text=(ROOT/"plugin.py").read_text(encoding="utf-8")
    assert "self.preview_timer.setInterval(35)" in text
