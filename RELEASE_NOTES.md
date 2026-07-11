# Änderungen

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
