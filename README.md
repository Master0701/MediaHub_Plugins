# MediaHub Plugins

Offizielles Erweiterungs-Repository für MediaHub.

## Aktueller Stand

- **MediaHub Metadata Editor 0.3.6**
- **MediaHub Mobile Dashboard 0.1.7**
- **MediaHub WebRemote 0.13.7**

# Ausstehende Release-Notizen

## MediaHub WebRemote v0.13.7

- Eigene Weboberfläche wieder aktiviert und über die normale Plugin-Verwaltung wieder direkt öffnbar.
- WebRemote bleibt aus dem zusätzlichen Bereich „Plugin-Oberflächen“ ausgeblendet.
- Die browserbasierte Plugin-Verwaltung und der neue Bereich für zusätzliche Web-Plugins bleiben erhalten.

## MediaHub Mobile Dashboard v0.1.7

- Eigene mobile Weboberfläche wieder aktiviert und über die normale Plugin-Verwaltung wieder direkt öffnbar.
- Mobile Dashboard bleibt aus dem zusätzlichen Bereich „Plugin-Oberflächen“ ausgeblendet.
- Die mobile Plugin-Verwaltung und der Bereich für zusätzliche Web-Plugins bleiben erhalten.

## MediaHub Metadata Editor v0.3.6

- Desktop- und Weboberfläche bleiben gemeinsam verfügbar.
- Der Metadata Editor bleibt als zusätzliche Plugin-Oberfläche in WebRemote und Mobile Dashboard sichtbar.
- Die Weboberfläche öffnet weiterhin in einem neuen Browser-Tab.

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
