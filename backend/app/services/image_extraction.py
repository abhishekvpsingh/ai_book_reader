import os
import fitz
from app.core.config import settings


def extract_images(doc: fitz.Document, book_id: int) -> list[dict]:
    assets = []
    book_dir = os.path.join(settings.image_dir, str(book_id))
    os.makedirs(book_dir, exist_ok=True)

    for page_index in range(doc.page_count):
        page = doc.load_page(page_index)
        image_list = page.get_images(full=True)
        for img_index, img in enumerate(image_list, start=1):
            xref = img[0]
            pix = fitz.Pixmap(doc, xref)
            if pix.n - pix.alpha >= 4:
                pix = fitz.Pixmap(fitz.csRGB, pix)
            filename = f"p{page_index + 1}_img{img_index}.png"
            file_path = os.path.join(book_dir, filename)
            pix.save(file_path)
            assets.append(
                {
                    "page_num": page_index + 1,
                    "file_path": file_path,
                    "caption": f"Page {page_index + 1} - Figure",
                }
            )
    return assets
