# AI Workflow Evaluator

AI Workflow Evaluator is a full web application that scores how effectively a person uses AI while coding, based on real transcript behavior.

## What it does

- Parses transcripts from JSON exports and plain text.
- Evaluates 7 workflow dimensions: planning, debugging, constraints, iteration, correction, tool usage, and repetition.
- Produces structured score output with confidence, evidence, strengths, weaknesses, and suggestions.
- Includes a web dashboard for transcript input, scoring visualization, and workflow insights.

## Project Structure

```text
ai-workflow-evaluator/
├── transcripts/
│   ├── session1.json
│   ├── session2.json
├── backend/
│   ├── main.py
│   ├── evaluator.py
│   ├── parser.py
│   ├── categories.py
│   ├── config.py
│   └── schemas.py
├── prompts/
│   ├── planning.txt
│   └── debugging.txt
├── frontend/
│   ├── index.html
│   └── app.js
├── requirements.txt
└── README.md
```

## How to run

```bash
pip install -r requirements.txt
uvicorn backend.main:app --reload --port 8000
```

Open `http://127.0.0.1:8000` in your browser.

## Quick test

```bash
curl -X POST "http://127.0.0.1:8000/evaluate" \
  -H "Content-Type: application/json" \
  -d "{\"transcript_path\": \"transcripts/session1.json\"}"
```

### API endpoints

- `GET /` - Web UI
- `GET /health` - Health check
- `GET /transcripts` - List bundled sample transcripts
- `POST /evaluate` - Evaluate from `transcript_text` or `transcript_path`
- `POST /evaluate/dashboard` - Chart-ready payload for frontend
- `POST /evaluate/upload` - Evaluate uploaded transcript file (multipart)

## Approach

- **Why these categories:** They cover core workflow behaviors that determine AI-assisted coding quality.
- **How evaluation works:** Each category is scored independently (1-5) with confidence, reasoning, and evidence.
- **Scoring:** Overall score is the average category score, then labeled as Poor, Average, Good, or Strong.
- **Trade-offs:** LLM-based judging increases flexibility and realism but introduces model variance; strict JSON and confidence reduce ambiguity.

## Configuration

Environment variables:

- `LLM_PROVIDER`: `mock` (default) or `openai`
- `OPENAI_API_KEY`: required for OpenAI mode
- `MODEL_NAME`: default `gpt-4o-mini`
- `MAX_CHUNK_CHARS`: transcript chunk limit per category (default `5000`)

If API credentials are missing, the service automatically falls back to mock heuristic scoring so development remains unblocked.
