# MediaHub Plugins – vollständiges Update

## Dateien kopieren

Den Inhalt dieses Pakets in den Hauptordner von `MediaHub-Plugins` kopieren.
Vorhandene Dateien überschreiben.

Wichtig: Im Ordner `plugins/web_remote/` wird nur `plugin.json` ersetzt.
Die übrigen Plugin-Dateien bleiben unverändert.

## Danach lokal prüfen

```powershell
python validate_plugins.py
python prepare_plugin_release.py
python build_plugins.py all --clean
```

## Git aktualisieren

Falls `RELEASE_NOTES_PENDING.md` bereits verfolgt wird:

```powershell
git rm --cached RELEASE_NOTES_PENDING.md
```

Danach:

```powershell
git add -A
git commit -m "MediaHub Plugins – WebRemote 0.5.2 und Node-24-Workflows"
git push origin main
```

## Release erstellen

```powershell
git tag -a v0.5.2 -m "MediaHub Plugins v0.5.2"
git push origin v0.5.2
```

Der Tag baut alle Plugins vollständig neu. Die GitHub-Release-Seite erhält automatisch
den Inhalt aus `RELEASE_NOTES.md`.

## Build-Entscheidung

Wegen der MediaHub-API-Kompatibilitätsänderung müssen diesmal alle Plugins gebaut werden:

```powershell
python build_plugins.py all --clean
```

## Nach erfolgreichem Release

`RELEASE_NOTES_PENDING.md` ist durch `.gitignore` nur lokal. Sie kann nach erfolgreichem
Release lokal gelöscht werden, ohne einen zusätzlichen Git-Commit zu erzeugen.
