from pathlib import Path
from services.rule_engine import RenameRuleEngine
from services.profile_service import ProfileService

ROOT=Path(__file__).resolve().parents[1]
def p(pid): return next(x for x in ProfileService(ROOT).list_profiles() if x["id"]==pid)

def test_all_library_profiles_keep_series_schema():
    for pid in ("plex","jellyfin","emby","kodi"):
        series=next(r for r in p(pid)["rules"] if r.get("media_types")==["series"])
        assert "[staffel]" in series["template"] and "[episode]" in series["template"]

def test_all_profiles_render_series_numbers():
    for pid in ("plex","jellyfin","emby","kodi"):
        result=RenameRuleEngine().apply("old.mkv",p(pid)["rules"],metadata={"media_type":"series","titel":"Serie","staffel":1,"episode":9,"episodentitel":"Folge"})
        assert result["proposed_name"]=="Serie - S01E09 - Folge.mkv",(pid,result)

def test_movie_rule_does_not_use_episode_fields():
    result=RenameRuleEngine().apply("old.mkv",p("plex")["rules"],metadata={"media_type":"movie","titel":"Film","jahr":2024,"staffel":1,"episode":2})
    assert result["proposed_name"]=="Film (2024).mkv"

def test_audiobook_unchanged():
    assert p("audiobook")["media_types"]==["audiobook"]

def test_schema_order_stored():
    series=next(r for r in p("plex")["rules"] if r.get("media_types")==["series"])
    assert series["schema_order"]==["[titel]","S[staffel]E[episode]","[episodentitel]"]

def test_desktop_order_ui_present():
    text=(ROOT/"plugin.py").read_text(encoding="utf-8")
    assert "Beschriftungs-Reihenfolge" in text and "_apply_schema_order" in text

def test_web_order_ui_present():
    text=(ROOT/"index.html").read_text(encoding="utf-8")
    assert 'id="schemaOrder"' in text and 'id="schemaApply"' in text
