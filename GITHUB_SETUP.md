# Einmalige GitHub-Einrichtung

Zuerst auf GitHub ein leeres Repository namens `MediaHub_Plugins` erstellen.

Dann im Projektordner:

```powershell
git init
git branch -M main
git add .
git commit -m "MediaHub_Plugins v0.3.0 - GitHub- und mhplugin-Basis"
git remote add origin https://github.com/Master0701/MediaHub_Plugins.git
git push -u origin main
```

Ersten Release auslösen:

```powershell
git tag -a v0.3.0 -m "MediaHub_Plugins v0.3.0"
git push origin v0.3.0
```

Vorher den vorhandenen Plugin-Code nach `plugins/WebRemote/` übernehmen.
Dort müssen `plugin.json` und der in `entry` genannte Einstiegspunkt vorhanden sein.
