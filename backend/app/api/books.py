import logging
from datetime import datetime
from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models import Book, Section, ReadingProgress
from app.schemas.book import BookOut
from app.schemas.section import SectionTree
from app.schemas.progress import ProgressOut, ProgressUpdate
from app.services.pdf_ingestion import save_pdf_file
from app.services.section_tree_builder import build_tree
from app.workers.rq_queue import get_queue
from app.workers import tasks

logger = logging.getLogger(__name__)

router = APIRouter()


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
        #viewer {{ flex:1; overflow:auto; background:#111318; }}
        #toolbar {{ display:flex; align-items:center; gap:8px; padding:8px 12px; background:#161a1f; border-bottom:1px solid #2a323d; position:sticky; top:0; z-index:2; }}
        #toolbar button {{ background:#202531; color:#e5e7eb; border:1px solid #2a323d; padding:4px 8px; border-radius:6px; cursor:pointer; }}
        #pdf-canvas {{ display:block; margin:16px auto; background:#fff; box-shadow:0 0 0 1px #2a323d; }}
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
            <span id="page-info"></span>
          </div>
          <canvas id="pdf-canvas"></canvas>
        </main>
      </div>
      <script src="https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js"></script>
      <script>
        const url = "{pdf_url}";
        let pdfDoc = null;
        let pageNumber = {page};
        const canvas = document.getElementById('pdf-canvas');
        const ctx = canvas.getContext('2d');
        const pageInfo = document.getElementById('page-info');
        const outlineEl = document.getElementById('outline');
        pdfjsLib.GlobalWorkerOptions.workerSrc = "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js";

        function renderPage(num) {{
          pdfDoc.getPage(num).then(function(page) {{
            const viewerWidth = document.getElementById('viewer').clientWidth - 40;
            const viewport = page.getViewport({{ scale: 1 }});
            const scale = viewerWidth / viewport.width;
            const scaledViewport = page.getViewport({{ scale }});
            canvas.height = scaledViewport.height;
            canvas.width = scaledViewport.width;
            const renderContext = {{ canvasContext: ctx, viewport: scaledViewport }};
            page.render(renderContext);
            pageInfo.textContent = `Page ${{num}} / ${{pdfDoc.numPages}}`;
          }});
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
            btn.style.paddingLeft = `${{8 + level * 12}}px`;
            btn.onclick = () => {{
              if (!item.dest) return;
              pdfDoc.getDestination(item.dest).then(dest => {{
                if (!dest) return;
                pdfDoc.getPageIndex(dest[0]).then(idx => {{
                  pageNumber = idx + 1;
                  renderPage(pageNumber);
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
    return HTMLResponse(content=html)


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
