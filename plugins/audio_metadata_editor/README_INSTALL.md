# MediaHub Audio Metadata Editor v0.0.1 – Source/Integration

Dieses ZIP ist für das MediaHub-Plugins-Repository gedacht.

1. `plugins/audio_metadata_editor/` ersetzt den bisherigen 0.0.0-Platzhalter.
2. Danach `python update_plugin_catalog.py`.
3. Danach `python validate_plugins.py`.
4. Danach `python -m pytest plugins/audio_metadata_editor/tests -q`.
5. Erst später die Dateien unter `integration/` als Vorlage verwenden, um
   `chromaprint_fpcalc` und `mp3tag` im MediaHub-Core Tool Manager zu
   registrieren und die zentralen Drittanbieterdateien zu ergänzen.
6. Der Metadata Editor wird durch dieses Paket absichtlich NICHT verändert.
