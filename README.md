# AI Book Reader & Smart Summary System

Production-ready Dockerized monorepo for ingesting PDFs, extracting structure + figures, and generating structured summaries with versioning and TTS.

## Quick Start (Mac Dev)
1) Copy env template:
```bash
cp .env.example .env
```
2) (Optional) Set `LLM_PROVIDER=openai` and `OPENAI_API_KEY=...` in `.env`, or configure Ollama.
3) Start the stack:
```bash
docker compose up --build
```
4) Open the UI:
- Streamlit: http://localhost:8501
- API docs: http://localhost:8000/docs

## Ollama Setup
- Install Ollama and pull a model:
```bash
ollama serve
ollama pull llama3
```
- Update `.env`:
```
LLM_PROVIDER=ollama
OLLAMA_URL=http://host.docker.internal:11434
OLLAMA_MODEL=llama3
```

## OpenAI Setup
Update `.env`:
```
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
```

## SQLite vs PostgreSQL
- SQLite (default): `DATABASE_URL=sqlite:////data/app.db`
- PostgreSQL (prod):
  - Use `docker compose --profile prod up --build` to start `postgres`.
  - Use `docker compose -f docker-compose.yml -f docker-compose.prod.yml --profile prod up --build`.
  - `.env` should include:
```
DATABASE_URL=postgresql+psycopg2://ai_book_reader:ai_book_reader@postgres:5432/ai_book_reader
```

## UGREEN NAS Deployment
1) Create a data directory on the NAS, e.g. `/volume1/docker/ai_book_reader/data`.
2) Map it to `/data` in `docker-compose.yml` (already set to `./data:/data`).
3) Copy the repo to the NAS and run:
```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml --profile prod up --build -d
```

## Backend Smoke Check
```bash
python backend/scripts/smoke_check.py http://localhost:8000
```

## Sanity Checklist
- Upload book: http://localhost:8501 (sidebar upload)
- Open PDF viewer: select a book and confirm the embedded viewer renders
- Jump to section: click a section and confirm page jumps to section start
- Generate summary: click section, open modal, hit Regenerate
- View images: confirm Figures show under summary
- Regenerate/version: use Regenerate + Versions dropdown
- Listen audio: click Listen and verify audio playback
- Delete version: click Delete and confirm versions list updates
- Summaries explorer: open tab and click nodes to open summary modal

## Data Layout
- PDFs: `/data/pdfs`
- Images: `/data/images/{book_id}/p{page}_img{n}.png`
- Audio: `/data/audio/{book_id}/{section_id}/{version_id}.wav|mp3`
