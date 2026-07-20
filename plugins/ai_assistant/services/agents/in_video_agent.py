from __future__ import annotations

from typing import Any


class InVideoAgent:
    """Planungsmodul für die spätere echte In-Video-Erkennung."""

    def capabilities(self) -> dict[str, Any]:
        return {
            "implemented": False,
            "planned_pipeline": [
                "Schlüsselbilder aus Vorspann, Abspann, Kapiteln und Szenenwechseln",
                "OCR für Titelkarten, Episodennummern, Logos und Credits",
                "Auswertung vorhandener Untertitel",
                "Audio-/Spracherkennung für markante Dialoge und Titelhinweise",
                "Bild- und Ton-Fingerprints",
                "Vergleich von Laufzeit und Szenenfolgen zur Schnittfassungserkennung",
            ],
            "edition_targets": [
                "Uncut", "Extended", "Director's Cut", "Theatrical Cut", "Remastered"
            ],
        }
