from __future__ import annotations

from pathlib import Path
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.config import load_settings
from backend.evaluator import evaluate_workflow
from backend.parser import parse_transcript_file, parse_transcript_text
from backend.schemas import CompareRequest, EvaluateRequest, EvaluationResponse

app = FastAPI(title="AI Workflow Evaluator", version="0.1.0")
settings = load_settings()
BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "frontend"
TRANSCRIPTS_DIR = BASE_DIR / "transcripts"

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


if STATIC_DIR.exists():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR), name="assets")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/")
def web_app() -> FileResponse:
    index_file = STATIC_DIR / "index.html"
    if not index_file.exists():
        raise HTTPException(status_code=404, detail="Frontend not found")
    return FileResponse(index_file)


def _evaluate_from_payload(payload: EvaluateRequest) -> EvaluationResponse:
    if payload.transcript_text:
        source_text = payload.transcript_text
        messages = parse_transcript_text(payload.transcript_text)
    elif payload.transcript_path:
        path = Path(payload.transcript_path)
        if not path.exists():
            raise HTTPException(status_code=404, detail=f"Transcript not found: {path}")
        source_text = path.read_text(encoding="utf-8")
        messages = parse_transcript_file(path)
    else:
        raise HTTPException(status_code=400, detail="Provide transcript_text or transcript_path")

    if not messages:
        raise HTTPException(status_code=400, detail="No parseable messages found in transcript")
    return evaluate_workflow(messages, settings, source_text=source_text)


@app.post("/evaluate", response_model=EvaluationResponse)
def evaluate(payload: EvaluateRequest) -> EvaluationResponse:
    return _evaluate_from_payload(payload)


@app.post("/evaluate/upload", response_model=EvaluationResponse)
async def evaluate_upload(file: UploadFile = File(...)) -> EvaluationResponse:
    content = await file.read()
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail="Uploaded file must be UTF-8 text/JSON.") from exc

    messages = parse_transcript_text(text)
    if not messages:
        raise HTTPException(status_code=400, detail="No parseable messages found in uploaded transcript")
    return evaluate_workflow(messages, settings, source_text=text)


@app.get("/transcripts")
def list_transcripts() -> dict[str, list[str]]:
    files = sorted([p.name for p in TRANSCRIPTS_DIR.glob("*") if p.is_file()])
    return {"files": files}


@app.get("/transcripts/{filename}")
def get_transcript_file(filename: str) -> dict[str, str]:
    target = (TRANSCRIPTS_DIR / filename).resolve()
    if not str(target).startswith(str(TRANSCRIPTS_DIR.resolve())):
        raise HTTPException(status_code=400, detail="Invalid transcript path")
    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="Transcript not found")
    return {"name": target.name, "content": target.read_text(encoding="utf-8")}


@app.post("/evaluate/dashboard")
def evaluate_dashboard(payload: EvaluateRequest) -> dict:
    result = _evaluate_from_payload(payload)
    chart = [{"category": name, "score": data.score, "confidence": data.confidence} for name, data in result.categories.items()]
    return {
        "overall_score": result.overall_score,
        "label": result.label,
        "chart_data": chart,
        "strengths": result.strengths,
        "weaknesses": result.weaknesses,
        "suggestions": result.suggestions,
        "summary": result.summary,
        "reflection": result.reflection,
        "transcript_format": result.transcript_format,
        "phase_timeline": result.phase_timeline,
        "metric_confidence": {name: data.confidence for name, data in result.categories.items()},
    }


@app.post("/compare")
def compare_sessions(payload: CompareRequest) -> dict:
    rows: list[dict] = []
    for session in payload.sessions:
        if session.transcript_text:
            text = session.transcript_text
        elif session.transcript_path:
            path = Path(session.transcript_path)
            if not path.exists():
                raise HTTPException(status_code=404, detail=f"Transcript not found: {path}")
            text = path.read_text(encoding="utf-8")
        else:
            raise HTTPException(status_code=400, detail=f"Session '{session.name}' needs transcript_text or transcript_path")

        messages = parse_transcript_text(text)
        if not messages:
            raise HTTPException(status_code=400, detail=f"No parseable messages in session '{session.name}'")
        evaluated = evaluate_workflow(messages, settings, source_text=text)
        rows.append(
            {
                "name": session.name,
                "overall_score": evaluated.overall_score,
                "label": evaluated.label,
                "categories": {key: value.score for key, value in evaluated.categories.items()},
                "confidence": {key: value.confidence for key, value in evaluated.categories.items()},
                "phase_timeline": evaluated.phase_timeline,
            }
        )

    rows = sorted(rows, key=lambda x: x["overall_score"], reverse=True)
    return {
        "sessions": rows,
        "best_session": rows[0]["name"],
        "score_spread": round(rows[0]["overall_score"] - rows[-1]["overall_score"], 2) if len(rows) > 1 else 0.0,
    }
