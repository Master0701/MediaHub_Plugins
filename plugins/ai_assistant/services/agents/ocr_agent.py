from __future__ import annotations

import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from services.input_quality import evaluate_text


class OCRAgent:
    def run(self,file_path:Path,ffmpeg:Path|None,tesseract:Path|None,sample_points:list[float])->dict[str,Any]:
        if ffmpeg is None: return {"state":"unavailable","reason":"ffmpeg wurde nicht gefunden."}
        if tesseract is None: return {"state":"unavailable","reason":"Tesseract ist nicht installiert."}
        findings=[]
        with tempfile.TemporaryDirectory(prefix="mediahub_ai_ocr_") as tmp:
            for idx,point in enumerate(sample_points[:6]):
                image=Path(tmp)/f"frame_{idx}.png"
                extract=[str(ffmpeg),"-hide_banner","-loglevel","error","-nostdin","-ss",str(max(0,point)),"-i",str(file_path),
                         "-frames:v","1","-vf","scale='min(1920,iw)':-2","-y",str(image)]
                try:
                    ep=subprocess.run(extract,capture_output=True,timeout=25,check=False,creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
                    if ep.returncode!=0 or not image.exists(): continue
                    op=subprocess.run([str(tesseract),str(image),"stdout","-l","deu+eng","--psm","11"],capture_output=True,text=True,
                                      encoding="utf-8",errors="replace",timeout=30,check=False,creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
                    text=re.sub(r"\s+"," ",op.stdout or "").strip()
                    quality=evaluate_text(text, source="ocr")
                    if len(text)>=3 and quality.accepted:
                        findings.append({"second":round(float(point),2),"text":text[:500],"quality":quality.as_dict()})
                    elif len(text)>=3:
                        findings.append({"second":round(float(point),2),"text":text[:500],"discarded":True,"quality":quality.as_dict()})
                except Exception as exc: findings.append({"second":round(float(point),2),"error":str(exc)})
        accepted=[f for f in findings if not f.get("discarded") and f.get("text")]
        combined=" ".join(f.get("text","") for f in accepted)
        episode_patterns=re.findall(r"\b(?:S\d{1,2}E\d{1,3}|Staffel\s*\d+|Episode\s*\d+|Folge\s*\d+)\b",combined,re.IGNORECASE)
        return {"state":"completed" if accepted else "no_text","findings":accepted,"discarded_findings":[f for f in findings if f.get("discarded")],"episode_hints":episode_patterns[:10],"quality_gate":{"accepted":len(accepted),"discarded":len(findings)-len(accepted)}}
