from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_provider_settings_gui_present():
    text=(ROOT/'plugin.py').read_text(encoding='utf-8')
    assert 'tabs.addTab(provider_page, "Online-Quellen")' in text
    assert 'TMDb Verbindung testen' in text
    assert 'TheTVDB Verbindung testen' in text

def test_source_manager_provider_settings_api_present():
    text=(ROOT/'services'/'source_manager.py').read_text(encoding='utf-8')
    assert 'def update_provider_settings(' in text
    assert 'def test_provider(' in text
    assert 'ProviderCredentialStore' in text

def test_credentials_not_written_to_sources_json():
    text=(ROOT/'services'/'provider_credential_store.py').read_text(encoding='utf-8')
    assert 'provider_credentials.dat' in text
    assert 'CryptProtectData' in text
    assert 'CryptUnprotectData' in text
