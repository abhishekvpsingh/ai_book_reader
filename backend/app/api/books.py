import logging
import os
import shutil
from datetime import datetime
from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse
from sqlalchemy.orm import Session
from app.core.config import settings
from app.db.session import get_db
from app.models import Book, Section, ReadingProgress, Note
from app.schemas.book import BookOut, BookUpdate
from app.schemas.section import SectionTree
from app.schemas.progress import ProgressOut, ProgressUpdate
from app.services.pdf_ingestion import save_pdf_file
from app.services.section_tree_builder import build_tree
from app.workers.rq_queue import get_queue
from app.workers import tasks

logger = logging.getLogger(__name__)

router = APIRouter()
_summary_clicks: dict[int, dict] = {}


@router.post("/books", response_model=BookOut)
async def upload_book(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    content = await file.read()
    book = Book(title=file.filename, file_path="")
    db.add(book)
    db.flush()
    file_path = save_pdf_file(book.id, file.filename, content)
    book.file_path = file_path
    db.commit()
    db.refresh(book)

    queue = get_queue()
    job = queue.enqueue(tasks.ingest_pdf_job, book.id)
    logger.info("Book uploaded", extra={"book_id": book.id, "job_id": job.id})
    return book


@router.get("/books", response_model=list[BookOut])
def list_books(db: Session = Depends(get_db)):
    return db.query(Book).order_by(Book.created_at.desc()).all()


@router.get("/books/{book_id}", response_model=BookOut)
def get_book(book_id: int, db: Session = Depends(get_db)):
    book = db.get(Book, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    return book


@router.put("/books/{book_id}", response_model=BookOut)
def update_book(book_id: int, payload: BookUpdate, db: Session = Depends(get_db)):
    book = db.get(Book, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    title = payload.title.strip()
    if not title:
        raise HTTPException(status_code=400, detail="Title cannot be empty")
    book.title = title
    db.commit()
    db.refresh(book)
    return book


@router.delete("/books/{book_id}")
def delete_book(book_id: int, db: Session = Depends(get_db)):
    book = db.get(Book, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    file_path = book.file_path
    image_root = os.path.join(settings.image_dir, str(book_id))
    audio_root = os.path.join(settings.audio_dir, str(book_id))
    db.query(Note).filter(Note.book_id == book_id).delete(synchronize_session=False)
    db.delete(book)
    db.commit()
    _summary_clicks.pop(book_id, None)
    for path in [file_path]:
        try:
            if path and os.path.exists(path):
                os.remove(path)
        except OSError:
            logger.warning("Failed to delete file", extra={"path": path, "book_id": book_id})
    for folder in [image_root, audio_root]:
        try:
            if os.path.isdir(folder):
                shutil.rmtree(folder)
        except OSError:
            logger.warning("Failed to delete folder", extra={"path": folder, "book_id": book_id})
    return {"status": "deleted"}


@router.get("/books/{book_id}/sections", response_model=list[SectionTree])
def get_book_sections(book_id: int, db: Session = Depends(get_db)):
    sections = db.query(Section).filter(Section.book_id == book_id).order_by(Section.sort_order).all()
    return build_tree(sections)


@router.get("/books/{book_id}/pdf")
def get_book_pdf(book_id: int, db: Session = Depends(get_db)):
    book = db.get(Book, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    headers = {
        "Content-Disposition": "inline",
        "Content-Security-Policy": "frame-ancestors *",
        "X-Frame-Options": "ALLOWALL",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Range",
        "Access-Control-Expose-Headers": "Accept-Ranges, Content-Range, Content-Length",
        "Accept-Ranges": "bytes",
    }
    return FileResponse(book.file_path, media_type="application/pdf", headers=headers)


@router.get("/books/{book_id}/viewer", response_class=HTMLResponse)
def get_book_viewer(book_id: int, request: Request, page: int = 1, db: Session = Depends(get_db)):
    book = db.get(Book, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    base_url = str(request.base_url).rstrip("/")
    pdf_url = f"{base_url}/books/{book_id}/pdf"
    html = f"""
    <!doctype html>
    <html>
    <head>
      <meta charset="utf-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1" />
      <style>
        html, body {{ margin:0; padding:0; height:100%; width:100%; background:#1b2027; color:#e5e7eb; }}
        #layout {{ display:flex; height:100vh; }}
        #sidebar {{ width:280px; background:#202531; border-right:1px solid #2a323d; overflow:auto; padding:12px; }}
        #sidebar h3 {{ margin:0 0 8px 0; font-size:14px; color:#cbd5e1; }}
        #outline {{ list-style:none; padding:0; margin:0; }}
        #outline li {{ margin:4px 0; }}
        #outline button {{ width:100%; text-align:left; background:transparent; color:#e5e7eb; border:0; padding:6px 8px; border-radius:6px; cursor:pointer; }}
        #outline button:hover {{ background:#2b3240; }}
        #viewer {{ flex:1; overflow:auto; background:#111318; position:relative; }}
        #toolbar {{ display:flex; align-items:center; gap:8px; padding:8px 12px; background:#161a1f; border-bottom:1px solid #2a323d; position:sticky; top:0; z-index:4; }}
        #toolbar button {{ background:#202531; color:#e5e7eb; border:1px solid #2a323d; padding:4px 8px; border-radius:6px; cursor:pointer; }}
        #toolbar input {{ width:56px; background:#202531; color:#e5e7eb; border:1px solid #2a323d; border-radius:6px; padding:4px 6px; }}
        #page-wrap {{ position:relative; margin:16px auto; width:fit-content; }}
        #pdf-canvas {{ display:block; background:#fff; box-shadow:0 0 0 1px #2a323d; }}
        #highlight-layer {{ position:absolute; left:0; top:0; z-index:4; pointer-events:none; }}
        #highlight-layer .hl {{ position:absolute; background:rgba(255, 213, 79, 0.35); border-radius:4px; pointer-events:auto; }}
        #text-layer {{ position:absolute; left:0; top:0; z-index:3; color:transparent; user-select:text; pointer-events:auto; }}
        #text-layer span {{ color:transparent; position:absolute; transform-origin:0% 0%; white-space:pre; cursor:pointer; }}
        .textLayer {{ user-select:text; }}
        #page-wrap {{ user-select:text; }}
        ::selection {{ background:rgba(255, 213, 79, 0.25); }}
        #ask-button {{ position:absolute; display:none; z-index:5; background:#1f2937; border:1px solid #374151; color:#e5e7eb; padding:6px 10px; border-radius:8px; cursor:pointer; }}
        #qa-panel {{ position:absolute; display:none; z-index:6; right:24px; top:72px; width:360px; background:#111827; border:1px solid #2a323d; border-radius:12px; padding:12px; box-shadow:0 12px 30px rgba(0,0,0,0.4); }}
        #qa-panel textarea {{ width:100%; background:#0b0f14; color:#e5e7eb; border:1px solid #2a323d; border-radius:8px; padding:8px; min-height:72px; }}
        #qa-panel .actions {{ display:flex; gap:8px; margin-top:8px; }}
        #qa-panel button {{ background:#202531; color:#e5e7eb; border:1px solid #2a323d; padding:6px 10px; border-radius:8px; cursor:pointer; }}
        #qa-answer {{ white-space:pre-wrap; background:#0b0f14; border:1px solid #2a323d; border-radius:8px; padding:8px; margin-top:8px; min-height:60px; }}
        #qa-status {{ color:#9ca3af; font-size:12px; margin-top:6px; }}
        @media (max-width: 1024px) {{
          #sidebar {{ display:none; width:0; padding:0; border:none; }}
          #viewer {{ width:100%; }}
          #qa-panel {{ right:12px; left:12px; width:auto; }}
        }}
      </style>
    </head>
    <body>
      <div id="layout">
        <aside id="sidebar">
          <h3>Outline</h3>
          <ul id="outline"></ul>
        </aside>
        <main id="viewer">
          <div id="toolbar">
            <button onclick="prevPage()">Prev</button>
            <button onclick="nextPage()">Next</button>
            <span>Page</span>
            <input id="page-input" type="number" min="1" />
            <span id="page-count"></span>
            <span style="margin-left:auto;"></span>
            <button onclick="zoomOut()">-</button>
            <span id="zoom-level">100%</span>
            <button onclick="zoomIn()">+</button>
          </div>
          <div id="page-wrap">
            <canvas id="pdf-canvas"></canvas>
            <div id="highlight-layer"></div>
            <div id="text-layer" class="textLayer"></div>
          </div>
          <div id="ask-button">Ask about selection</div>
          <div id="qa-panel">
            <strong>Ask a question</strong>
            <textarea id="qa-question" placeholder="Type your question..."></textarea>
            <div class="actions">
              <button id="qa-ask">Ask</button>
              <button id="qa-save" disabled>Save note</button>
              <button id="qa-close">Close</button>
            </div>
            <div id="qa-answer"></div>
            <div id="qa-status"></div>
          </div>
        </main>
      </div>
      <script src="https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js"></script>
      <script>
        const url = "{pdf_url}";
        const apiBase = "{base_url}";
        const bookId = {book_id};
        let pdfDoc = null;
        let pageNumber = {page};
        let zoomScale = 0.9;
        let lastSelection = null;
        let currentAnswer = "";
        const canvas = document.getElementById('pdf-canvas');
        const ctx = canvas.getContext('2d');
        const textLayer = document.getElementById('text-layer');
        const highlightLayer = document.getElementById('highlight-layer');
        const pageInfo = document.getElementById('page-count');
        const pageInput = document.getElementById('page-input');
        const outlineEl = document.getElementById('outline');
        const askButton = document.getElementById('ask-button');
        const qaPanel = document.getElementById('qa-panel');
        const qaQuestion = document.getElementById('qa-question');
        const qaAnswer = document.getElementById('qa-answer');
        const qaAskBtn = document.getElementById('qa-ask');
        const qaSaveBtn = document.getElementById('qa-save');
        const qaCloseBtn = document.getElementById('qa-close');
        const qaStatus = document.getElementById('qa-status');
        pdfjsLib.GlobalWorkerOptions.workerSrc = "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js";

        function emitSummaryEvent(page) {{
          const eventId = Date.now();
          try {{
            window.parent.postMessage(
              {{ type: "section_summary", book_id: bookId, page: page, event_id: eventId }},
              "*"
            );
          }} catch (err) {{
            console.error(err);
          }}
          fetch(apiBase + "/books/" + bookId + "/summary_click", {{
            method: "POST",
            headers: {{ "Content-Type": "application/json" }},
            body: JSON.stringify({{ page: page, event_id: eventId }})
          }}).catch(() => {{}});
        }}

        function clearSelectionUI() {{
          askButton.style.display = "none";
          qaPanel.style.display = "none";
          qaQuestion.value = "";
          qaAnswer.textContent = "";
          qaStatus.textContent = "";
          qaSaveBtn.disabled = true;
          currentAnswer = "";
        }}

        function renderHighlights(notes) {{
          highlightLayer.innerHTML = "";
          notes.forEach(note => {{
            (note.rects || []).forEach(rect => {{
              const div = document.createElement('div');
              div.className = "hl";
              div.style.left = (rect.x * canvas.width) + "px";
              div.style.top = (rect.y * canvas.height) + "px";
              div.style.width = (rect.w * canvas.width) + "px";
              div.style.height = (rect.h * canvas.height) + "px";
              div.title = note.question;
              div.onclick = (event) => {{
                event.stopPropagation();
                event.preventDefault();
                qaQuestion.value = note.question;
                qaAnswer.textContent = note.answer;
                qaStatus.textContent = "Saved note";
                qaSaveBtn.disabled = true;
                qaPanel.style.display = "block";
              }};
              highlightLayer.appendChild(div);
            }});
          }});
        }}

        highlightLayer.addEventListener('click', function(event) {{
          if (event.target && event.target.classList && event.target.classList.contains('hl')) {{
            event.stopPropagation();
          }}
        }});

        function loadNotes(page) {{
          fetch(apiBase + "/books/" + bookId + "/notes?page=" + page)
            .then(resp => resp.ok ? resp.json() : [])
            .then(data => renderHighlights(data))
            .catch(() => renderHighlights([]));
        }}

        function renderTextLayer(page, viewport) {{
          return page.getTextContent().then(textContent => {{
            textLayer.innerHTML = "";
            textLayer.style.height = viewport.height + "px";
            textLayer.style.width = viewport.width + "px";
            return pdfjsLib.renderTextLayer({{
              textContent: textContent,
              container: textLayer,
              viewport: viewport,
              textDivs: []
            }}).promise;
          }});
        }}

        function renderPage(num) {{
          pdfDoc.getPage(num).then(function(page) {{
            const viewerWidth = document.getElementById('viewer').clientWidth - 40;
            const viewport = page.getViewport({{ scale: 1 }});
            const scale = (viewerWidth / viewport.width) * zoomScale;
            const scaledViewport = page.getViewport({{ scale: scale }});
            canvas.height = scaledViewport.height;
            canvas.width = scaledViewport.width;
            textLayer.style.height = scaledViewport.height + "px";
            textLayer.style.width = scaledViewport.width + "px";
            textLayer.style.setProperty("--scale-factor", scaledViewport.scale);
            highlightLayer.style.height = scaledViewport.height + "px";
            highlightLayer.style.width = scaledViewport.width + "px";
            const renderContext = {{ canvasContext: ctx, viewport: scaledViewport }};
            page.render(renderContext).promise.then(() => {{
              renderTextLayer(page, scaledViewport);
              loadNotes(num);
            }});
            pageInfo.textContent = "of " + pdfDoc.numPages;
            pageInput.value = num;
            document.getElementById('zoom-level').textContent = Math.round(zoomScale * 100) + "%";
            clearSelectionUI();
          }});
        }}

        function zoomIn() {{
          zoomScale = Math.min(1.6, Math.round((zoomScale + 0.1) * 10) / 10);
          renderPage(pageNumber);
        }}

        function zoomOut() {{
          zoomScale = Math.max(0.6, Math.round((zoomScale - 0.1) * 10) / 10);
          renderPage(pageNumber);
        }}

        function nextPage() {{
          if (pageNumber >= pdfDoc.numPages) return;
          pageNumber += 1;
          renderPage(pageNumber);
        }}

        function prevPage() {{
          if (pageNumber <= 1) return;
          pageNumber -= 1;
          renderPage(pageNumber);
        }}

        function buildOutline(outline, level=0) {{
          if (!outline) return;
          outline.forEach(item => {{
            const li = document.createElement('li');
            const btn = document.createElement('button');
            btn.textContent = item.title || 'Untitled';
            btn.style.paddingLeft = (8 + level * 12) + "px";
            btn.onclick = () => {{
              if (!item.dest) return;
              const resolveDest = () => {{
                if (typeof item.dest === "string") {{
                  return pdfDoc.getDestination(item.dest);
                }}
                return Promise.resolve(item.dest);
              }};
              resolveDest().then(dest => {{
                if (!dest || !dest.length) return;
                const pageRef = dest[0];
                pdfDoc.getPageIndex(pageRef).then(idx => {{
                  pageNumber = idx + 1;
                  renderPage(pageNumber);
                  emitSummaryEvent(pageNumber);
                }}).catch(() => {{
                  if (typeof pageRef === "number") {{
                    pageNumber = pageRef + 1;
                    renderPage(pageNumber);
                    emitSummaryEvent(pageNumber);
                  }}
                }});
              }});
            }};
            li.appendChild(btn);
            outlineEl.appendChild(li);
            if (item.items && item.items.length) {{
              buildOutline(item.items, level + 1);
            }}
          }});
        }}

        function getSelectionRects() {{
          const selection = window.getSelection();
          if (!selection || selection.rangeCount === 0) return [];
          const range = selection.getRangeAt(0);
          const rects = Array.from(range.getClientRects());
          const wrap = document.getElementById('page-wrap');
          const wrapRect = wrap.getBoundingClientRect();
          return rects
            .filter(r => r.width > 2 && r.height > 2)
            .map(r => {{
              return {{
                x: (r.left - wrapRect.left) / wrapRect.width,
                y: (r.top - wrapRect.top) / wrapRect.height,
                w: r.width / wrapRect.width,
                h: r.height / wrapRect.height
              }};
            }});
        }}

        document.addEventListener('mouseup', function() {{
          const selection = window.getSelection();
          if (!selection || selection.isCollapsed) {{
            askButton.style.display = "none";
            return;
          }}
          const range = selection.getRangeAt(0);
          if (!textLayer.contains(range.commonAncestorContainer)) {{
            askButton.style.display = "none";
            return;
          }}
          const rect = range.getBoundingClientRect();
          const viewerRect = document.getElementById('viewer').getBoundingClientRect();
          askButton.style.left = (rect.left - viewerRect.left) + "px";
          askButton.style.top = (rect.top - viewerRect.top - 36) + "px";
          askButton.style.display = "block";
          lastSelection = {{
            text: selection.toString(),
            rects: getSelectionRects()
          }};
        }});

        textLayer.addEventListener('click', function(e) {{
          const selection = window.getSelection();
          if (selection && !selection.isCollapsed) return;
          const target = e.target;
          if (target && target.tagName === "SPAN" && (target.textContent || "").trim().length > 2) {{
            emitSummaryEvent(pageNumber);
          }}
        }});

        askButton.addEventListener('click', function() {{
          if (!lastSelection || !lastSelection.text) return;
          qaPanel.style.display = "block";
          qaAnswer.textContent = "";
          qaStatus.textContent = "";
          qaSaveBtn.disabled = true;
        }});

        qaCloseBtn.addEventListener('click', function() {{
          qaPanel.style.display = "none";
        }});

        qaAskBtn.addEventListener('click', function() {{
          if (!lastSelection || !lastSelection.text) return;
          const question = qaQuestion.value.trim();
          if (!question) return;
          qaStatus.textContent = "Thinking...";
          fetch(apiBase + "/books/" + bookId + "/qa", {{
            method: "POST",
            headers: {{ "Content-Type": "application/json" }},
            body: JSON.stringify({{
              selection_text: lastSelection.text,
              question: question
            }})
          }}).then(resp => resp.json()).then(data => {{
            currentAnswer = data.answer || "";
            qaAnswer.textContent = currentAnswer || "No answer returned.";
            qaStatus.textContent = "Answer ready.";
            qaSaveBtn.disabled = !currentAnswer;
          }}).catch(() => {{
            qaStatus.textContent = "Failed to get answer.";
          }});
        }});

        qaSaveBtn.addEventListener('click', function() {{
          if (!lastSelection || !currentAnswer) return;
          const question = qaQuestion.value.trim();
          fetch(apiBase + "/books/" + bookId + "/notes", {{
            method: "POST",
            headers: {{ "Content-Type": "application/json" }},
            body: JSON.stringify({{
              page_num: pageNumber,
              selection_text: lastSelection.text,
              question: question,
              answer: currentAnswer,
              rects: lastSelection.rects || []
            }})
          }}).then(resp => resp.json()).then(() => {{
            qaStatus.textContent = "Saved note.";
            qaSaveBtn.disabled = true;
            loadNotes(pageNumber);
          }}).catch(() => {{
            qaStatus.textContent = "Failed to save note.";
          }});
        }});

        pageInput.addEventListener('change', function() {{
          const val = parseInt(pageInput.value || "1", 10);
          if (!pdfDoc) return;
          if (val < 1 || val > pdfDoc.numPages) return;
          pageNumber = val;
          renderPage(pageNumber);
        }});

        pdfjsLib.getDocument(url).promise.then(function(pdf) {{
          pdfDoc = pdf;
          if (pageNumber < 1) pageNumber = 1;
          if (pageNumber > pdfDoc.numPages) pageNumber = pdfDoc.numPages;
          renderPage(pageNumber);
          pdfDoc.getOutline().then(buildOutline);
        }}).catch(function(err) {{
          document.body.innerHTML = "<div style='padding:16px;color:#fff;'>Failed to load PDF page.</div>";
          console.error(err);
        }});
      </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html, headers={"Cache-Control": "no-store"})


@router.post("/books/{book_id}/summary_click")
def set_summary_click(book_id: int, payload: dict):
    page = payload.get("page")
    event_id = payload.get("event_id")
    if not page or not event_id:
        raise HTTPException(status_code=400, detail="page and event_id are required")
    _summary_clicks[book_id] = {"page": int(page), "event_id": int(event_id)}
    return {"status": "ok"}


@router.get("/books/{book_id}/summary_click")
def get_summary_click(book_id: int):
    data = _summary_clicks.pop(book_id, None)
    if not data:
        return {}
    return data


@router.get("/books/{book_id}/progress", response_model=ProgressOut)
def get_progress(book_id: int, db: Session = Depends(get_db)):
    progress = db.query(ReadingProgress).filter(ReadingProgress.book_id == book_id).first()
    if not progress:
        raise HTTPException(status_code=404, detail="Progress not found")
    return progress


@router.put("/books/{book_id}/progress", response_model=ProgressOut)
def update_progress(book_id: int, payload: ProgressUpdate, db: Session = Depends(get_db)):
    progress = db.query(ReadingProgress).filter(ReadingProgress.book_id == book_id).first()
    if not progress:
        progress = ReadingProgress(book_id=book_id, last_page=payload.last_page, last_section_id=payload.last_section_id)
        db.add(progress)
    else:
        progress.last_page = payload.last_page
        progress.last_section_id = payload.last_section_id
        progress.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(progress)
    return progress
