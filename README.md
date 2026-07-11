# MediaHub Plugins

Offizielles Erweiterungs-Repository für MediaHub.

## Aktueller Stand

- **MediaHub WebRemote 0.5.2**

## WebRemote 0.5.2

### Kompatibilität

- Mindestversion auf MediaHub v1.0.5 angehoben.
- Kompatibilität mit dem aktuellen MediaHub-API-Fix hergestellt.

### Build und Veröffentlichung

- GitHub Actions auf Node-24-kompatible Versionen aktualisiert.
- `actions/checkout` auf Version 6 aktualisiert.
- `actions/setup-python` auf Version 6 aktualisiert.
- `actions/upload-artifact` auf Version 6 aktualisiert.
- `softprops/action-gh-release` auf Version 3 aktualisiert.
- Release-Beschreibung wird automatisch aus `RELEASE_NOTES.md` übernommen.
- Zusätzliche Absicherung der Release-Beschreibung über `actions/github-script@v8`.
- README und Build-Anleitungen auf den aktuellen Projektstand gebracht.
- Build-Ausgabe korrekt auf den Ordner `release/` dokumentiert.

## Kompatibilität

Die aktuellen Plugins benötigen mindestens **MediaHub v1.0.5**.

## Projektaufbau

- `plugins/` – getrennte, einzeln installierbare Plugins
- `shared/` – gemeinsam genutzte Laufzeiten, APIs und Design-Bausteine
- `catalog/` – zukünftiger Download- und Updatekatalog
- `docs/` – Architektur-, Design- und Entwicklungsunterlagen
- `release/` – lokal und in GitHub Actions erzeugte Plugin-Pakete

Jedes Plugin bleibt optional und kann einzeln installiert, aktualisiert und entfernt werden.

## Plugins bauen

Alle Plugins sauber neu erstellen:

```powershell
python build_plugins.py all --clean
```

Nur WebRemote erstellen:

```powershell
python build_plugins.py web_remote --clean
```

Die fertigen `.mhplugin`-Dateien und `.sha256`-Prüfsummen liegen anschließend unter `release/`.

## Release vorbereiten

```powershell
python prepare_plugin_release.py
```

Dieser Befehl übernimmt `RELEASE_NOTES_PENDING.md` in die verfolgte Datei
`RELEASE_NOTES.md` und aktualisiert diese README. Die temporäre Pending-Datei
bleibt lokal und wird nicht in Git aufgenommen.
