# AI Book Reader & Smart Summary System

AI-powered book reader that ingests PDFs, extracts a structured section tree, and generates versioned summaries with figures and TTS. Runs as a Dockerized monorepo (FastAPI + Streamlit + RQ + Redis) on Mac and NAS.

## Workflow Overview
1) Upload a PDF.
2) Ingestion extracts text, TOC/heading-based sections, and embedded images.
3) Sections appear in the tree; click a node to generate summaries (recursive supported).
4) Summaries are versioned and shown in a modal with figures and TTS playback.
5) PDF viewer preserves the original layout and supports outline navigation.

## Quick Start (Mac)
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

## PDF Viewer
The app uses a local PDF.js viewer served by the backend:
```
GET /books/{id}/viewer?page=#
```
This avoids mixed-content issues on NAS and works on both Mac and NAS. On phones, the outline sidebar is hidden so the page is readable.

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
- PostgreSQL (optional):
  - Use `docker compose --profile prod up --build` to start `postgres`.
  - Use `docker compose -f docker-compose.yml -f docker-compose.prod.yml --profile prod up --build`.
  - `.env` should include:
```
DATABASE_URL=postgresql+psycopg2://ai_book_reader:ai_book_reader@postgres:5432/ai_book_reader
```

## UGREEN NAS Deployment
1) Create a data directory on the NAS, e.g. `/volume2/docker/ai_book_reader/data`.
2) Map it to `/data` in `docker-compose.yml` (already set to `./data:/data`).
3) Copy the repo to the NAS and run:
```bash
docker compose up --build -d
```
4) For Tailscale access, expose port 8000 and set:
```
PUBLIC_BACKEND_URL=http://<TAILSCALE_IP>:8000
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
