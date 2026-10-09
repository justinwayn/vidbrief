"""
VidBrief MVP — FastAPI server.

Endpoints:
  GET  /                 -> serves the web app
  POST /api/summarize    -> {"transcript": str, "title": str} -> summary JSON
  POST /api/markdown     -> same input -> {"markdown": str} (copy-ready)
  GET  /api/health       -> {"ok": true, "ollama": bool}

Zero-budget: no paid APIs, no cloud. Local Ollama if present, else heuristics.

Run:  uvicorn main:app --host 0.0.0.0 --port 8091
      (or: python3 main.py)
"""
import os
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from summarizer import summarize, to_markdown, _ollama_models

BASE = os.path.dirname(os.path.abspath(__file__))
STATIC = os.path.join(BASE, "static")

app = FastAPI(title="VidBrief", version="0.1.0")
app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/")
def index():
    return FileResponse(os.path.join(STATIC, "index.html"))


class SummarizeIn(BaseModel):
    transcript: str
    title: str = "Meeting Brief"


@app.get("/api/health")
def health():
    models = _ollama_models()
    return {"ok": True, "ollama_available": bool(models), "ollama_models": models}


@app.post("/api/summarize")
def api_summarize(body: SummarizeIn):
    if not body.transcript or len(body.transcript.strip()) < 30:
        raise HTTPException(status_code=400, detail="Transcript too short.")
    result = summarize(body.transcript)
    if result.get("error"):
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@app.post("/api/markdown")
def api_markdown(body: SummarizeIn):
    if not body.transcript or len(body.transcript.strip()) < 30:
        raise HTTPException(status_code=400, detail="Transcript too short.")
    result = summarize(body.transcript)
    if result.get("error"):
        raise HTTPException(status_code=400, detail=result["error"])
    return {"markdown": to_markdown(result, body.title), "engine": result["engine"]}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8091)
