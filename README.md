# MediaHub Plugins

Eigenständiges Repository für die offizielle MediaHub-Produktfamilie.

## Produkte

- `web_remote` – lokales MediaHub Control Center im Browser
- `mobile_dashboard` – mobile Erweiterung auf derselben Server- und API-Basis
- `metadata_editor` – späterer Metadaten-Editor
- `ai_assistant` – spätere KI-Unterstützung
- `smart_renamer` – späteres intelligentes Massen-Umbenennungstool

## Projektaufbau

- `plugins/` – voneinander getrennte Plugins
- `shared/` – gemeinsam verwendbare Laufzeiten, APIs und Design-Bausteine
- `catalog/` – späterer Download- und Updatekatalog für MediaHub
- `docs/` – Architektur-, Design- und Entwicklungsregeln
- `dist/` – gebaute `.mhplugin`-Pakete

Jedes Plugin wird einzeln gebaut, veröffentlicht, installiert, aktualisiert und entfernt.

## Aktueller Stand

WebRemote 0.2 kann über die MediaHub-Plugin-Brücke gestartet und gestoppt werden und liest erste Statusdaten. Als nächster Entwicklungsschritt folgt Version 0.3 mit dem Control-Center-Grundlayout.

## Bauen

```powershell
python build_plugins.py web_remote
```

Das Build-Skript verwendet die vorhandene Python-Umgebung. Für das reine Plugin-Paket ist keine erneute PyInstaller-Installation erforderlich.
