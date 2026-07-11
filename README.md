# MediaHub Plugins

Eigenständiges Repository für die offizielle MediaHub-Produktfamilie.

## Produkte

- `web_remote` – lokales MediaHub Control Center im Browser
- `mobile_dashboard` – mobile Erweiterung auf derselben Server- und API-Basis
- `metadata_editor` – späterer Metadaten-Editor
- `ai_assistant` – spätere KI-Unterstützung
- `smart_renamer` – späteres intelligentes Massen-Umbenennungstool

## Aktueller Stand

WebRemote **v0.5.3** basiert auf MediaHub **v1.0.5** und enthält Live-Dashboard, Kanalübersicht, Live-Downloads und Warteschlange.

Jedes Plugin bleibt einzeln installierbar. Gemeinsame Bausteine liegen unter `shared/`.

## Prüfen und bauen

```powershell
python validate_plugins.py
python build_plugins.py all --clean
```

Die fertigen Pakete und SHA-256-Prüfsummen liegen unter `release/`.
