# AI Book Reader & Smart Summary System

A production‑ready, self‑hosted book reader for PDF textbooks that preserves original layout, builds a structured section tree, and generates versioned summaries with figures and TTS. Runs as a Dockerized monorepo (FastAPI + Streamlit + RQ + Redis) on Mac and NAS.

## Highlights
- Embedded PDF.js viewer with outline navigation, page jump, and zoom controls.
- Section tree from TOC or heading inference.
- Click‑to‑summarize directly from the PDF viewer (outline or page text).
- Versioned summaries with figures and audio playback (TTS).
- “Ask about selection” Q&A with saved, page‑anchored notes and highlights.
- Rename/Delete books from the sidebar (under “Manage book”).

## Workflow Overview
1) Upload a PDF.
2) Ingestion extracts text, sections (TOC/heading inference), and images.
3) Read the book in the embedded PDF viewer.
   - Click an outline item or a page heading to open a summary popup for that section.
   - Select text, ask a question, and optionally save a note to highlight the text.
4) Summaries are versioned and displayed with figures and TTS.

## Screenshots
Reader landing view and upload panel.

![Reader landing](docs/screenshots/Screenshot%202025-12-30%20at%206.36.03%20PM.png)

PDF viewer with outline navigation and zoom.

![PDF viewer](docs/screenshots/Screenshot%202025-12-30%20at%206.36.28%20PM.png)

Summary dialog with versions, figures, and audio controls.

![Summary dialog](docs/screenshots/Screenshot%202025-12-30%20at%206.36.41%20PM.png)

Ask about selection with saved note highlight.

![Ask about selection](docs/screenshots/Screenshot%202025-12-30%20at%206.37.00%20PM.png)
## Quick Start (Mac)
1) Copy env template:
```bash
cp .env.example .env
```
2) (Optional) Configure LLM provider:
- OpenAI: set `LLM_PROVIDER=openai` and `OPENAI_API_KEY=...`
- Ollama: see setup below
3) Start the stack:
```bash
docker compose up --build
```
4) Open the UI:
- Streamlit: http://localhost:8501
- API docs: http://localhost:8000/docs

## PDF Viewer
The app serves a local PDF.js viewer from the backend:
```
GET /books/{id}/viewer?page=#
```
It works on both Mac and NAS and avoids mixed‑content issues. On phones, the outline sidebar is hidden for readability.

## Ask About Selection (Q&A Notes)
- Select text on a page → click “Ask about selection”.
- Ask a question → save the answer as a note.
- Saved notes appear as highlights on the same page; click a highlight to open the saved Q&A.

## Book Management
- Rename or delete books from the sidebar under **Manage book**.
- Delete removes the book, notes, images, and audio from storage.

## Ollama Setup
```bash
ollama serve
ollama pull llama3
```
Update `.env`:
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
  - Or: `docker compose -f docker-compose.yml -f docker-compose.prod.yml --profile prod up --build`
  - `.env`:
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
4) For Tailscale access, set:
```
PUBLIC_BACKEND_URL=http://<TAILSCALE_IP>:8000
```

## Backend Smoke Check
```bash
python backend/scripts/smoke_check.py http://localhost:8000
```

## Sanity Checklist
- Upload book: http://localhost:8501 (sidebar upload)
- Read PDF: viewer renders pages and outline in the Reader tab
- Jump to section: outline click jumps to page
- Generate summary: click outline item or page heading → popup opens
- Versioning: use Regenerate and Versions dropdown
- Figures: show under the Figures tab in the summary popup
- Listen: generate and play audio
- Ask about selection: select text → Ask → Save → click highlight to reopen
- Summaries explorer: browse and open summaries by tree
- Rename/Delete: sidebar → Manage book

## Data Layout
- PDFs: `/data/pdfs`
- Images: `/data/images/{book_id}/p{page}_img{n}.png`
- Audio: `/data/audio/{book_id}/{section_id}/{version_id}.wav|mp3`
