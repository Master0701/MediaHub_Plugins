# MediaHub Plugins

Eigenständiges Repository für die offizielle MediaHub-Produktfamilie. Alle Plugins liegen getrennt in eigenen Ordnern, bleiben einzeln installierbar und verwenden gemeinsame Bausteine aus `shared/`.

## Aktueller Stand

**MediaHub WebRemote v0.11.0**

WebRemote ist ein lokales MediaHub Control Center für Desktop, Tablet und Smartphone. Es bietet Dashboard, Kanäle, Playlists, Bibliothek, Live-Downloads, Jobs, Scheduler, Statistiken, Aktivitäten und den vollständigen Start-/Download-Assistenten direkt im Browser. Downloads aus dem Web-Assistenten werden ohne zusätzliches MediaHub-Dialogfenster gestartet und live im Browser angezeigt.

## Produktfamilie

- `web_remote` – lokales MediaHub Control Center im Browser
- `mobile_dashboard` – mobile Erweiterung auf derselben Server- und API-Basis
- `metadata_editor` – geplanter Metadaten-Editor
- `ai_assistant` – geplante KI-Unterstützung
- `smart_renamer` – geplantes intelligentes Massen-Umbenennungstool

## Prüfen und bauen

```powershell
python validate_plugins.py
python build_plugins.py all --clean
```

Die fertigen `.mhplugin`-Pakete und SHA-256-Prüfsummen werden unter `release/` erzeugt.

## Repositories

- Hauptprogramm: `Master0701/MediaHub`
- Plugins: `Master0701/MediaHub_Plugins`


## Gemeinsame Web Runtime

WebRemote und das spätere Mobile Dashboard verwenden dieselbe lokale Serverbasis. Jedes Plugin bringt die benötigte Runtime mit und bleibt einzeln installierbar. Sind mehrere Web-Plugins installiert, verwenden sie dieselben Netzwerk- und Geräte-Einstellungen.
