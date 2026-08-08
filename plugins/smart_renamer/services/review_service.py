from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any

@dataclass(slots=True)
class ReviewReason:
    code: str
    label: str
    severity: str = "review"
    message: str = ""
    def to_dict(self) -> dict[str, Any]: return asdict(self)

class ReviewService:
    RELATIONS={
      "split_episode":("Geteilte Episode","Prüfen, ob eine Episode wirklich auf mehrere Dateien verteilt ist."),
      "multi_episode":("Mehrere Episoden in einer Datei","Prüfen, ob wirklich mehrere Episoden in einer Datei enthalten sind."),
      "split_movie":("Geteilter Film","Prüfen, ob ein Film nur technisch auf mehrere Dateien verteilt wurde."),
      "multi_part":("Mehrteiliger Inhalt","Prüfen, ob die Teile zusammengehören."),
      "unknown_relation":("Unklare Medienbeziehung","Die Beziehung ist noch nicht eindeutig."),
    }
    def classify(self,row:dict[str,Any])->list[dict[str,Any]]:
        reasons=[]
        relation=str(row.get("relation_type") or "single")
        if relation in self.RELATIONS:
            label,msg=self.RELATIONS[relation]
            reasons.append(ReviewReason(relation,label,"review",msg))
        confidence=float(row.get("confidence") or 0)
        if confidence and confidence<0.75:
            reasons.append(ReviewReason("low_confidence","Niedrige Sicherheit","review",f"Erkennungssicherheit nur {confidence*100:.0f}%."))
        if row.get("review_required") and not reasons:
            reasons.append(ReviewReason("generic_review","Bitte prüfen","review","Die Erkennung verlangt eine manuelle Prüfung."))
        return [x.to_dict() for x in reasons]
    def needs_human_review(self,row:dict[str,Any])->bool:
        return bool(row.get("review_required") or str(row.get("relation_type") or "single") in self.RELATIONS)
