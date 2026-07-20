from __future__ import annotations

class MediaHubAudiobookManagerPlugin:
    """Vorbereitetes Plugin-Gerüst. Noch ohne aktive Fachfunktionen."""

    def __init__(self, api=None):
        self.api = api
        self.started = False

    def start(self):
        self.started = True
        return True

    def stop(self):
        self.started = False
        return True

    def get_status(self):
        return {
            "ready": False,
            "planned": True,
            "message": "Plugin-Gerüst vorhanden; Entwicklung noch nicht begonnen.",
        }
