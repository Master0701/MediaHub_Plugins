# Reservierte Metadata-Editor-Schnittstelle

Noch **nicht** in den Metadata Editor einbauen, solange dort weitergearbeitet
wird.

Vorgemerkt:
- Provider-Contract: `mediahub.audio_metadata.v1`
- Metadata-Bridge: `metadata.audio.bridge.v1`
- Provider optional, keine harte Plugin-Abhängigkeit
- Operationen: inspect, identify, compare, plan_write, apply_write
- apply_write immer mit Benutzerbestätigung, Backup und Rückleseprüfung

Dadurch kann die Bridge später ergänzt werden, ohne die Audio-Engine noch
einmal umzubauen.
