from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def test_web_workspace_is_responsive_and_shared():
    html=(ROOT/'index.html').read_text(encoding='utf-8')
    css=(ROOT/'assets/css/mediahub.css').read_text(encoding='utf-8')
    assert 'Regelstapel' in html
    assert '/smart-renamer/api/profiles' in html
    assert '/smart-renamer/api/preview' in html
    assert 'Live' in html
    assert '@media(max-width:980px)' in css
    assert '@media(max-width:560px)' in css

def test_desktop_workspace_has_three_areas_and_sources():
    source=(ROOT/'plugin.py').read_text(encoding='utf-8')
    assert 'Regelstapel' in source
    assert 'Regel-Eigenschaften' in source
    assert 'Vorschau' in source
    for name in ('Benutzer','Profil','KI','ReNamer','Plugin'):
        assert name in source
