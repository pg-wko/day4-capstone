import os
import tempfile
from pathlib import Path

from markitdown import MarkItDown
import pypdf

_md = MarkItDown()


def _markitdown_page(page: pypdf.PageObject) -> str:
    """Write a single page to a temp PDF and parse it with markitdown."""
    writer = pypdf.PdfWriter()
    writer.add_page(page)
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        writer.write(tmp)
        tmp_path = tmp.name
    try:
        return _md.convert(tmp_path).text_content.strip()
    finally:
        os.unlink(tmp_path)


def _chunk_words(text: str, chunk_size: int, overlap: int) -> list[str]:
    words = text.split()
    chunks, i = [], 0
    while i < len(words):
        chunks.append(" ".join(words[i : i + chunk_size]))
        i += chunk_size - overlap
    return chunks


def ingest_pdfs(
    pdf_dir: Path, chunk_size: int = 500, overlap: int = 50
) -> list[dict]:
    chunks = []
    pdf_files = list(pdf_dir.glob("*.pdf"))
    if not pdf_files:
        return chunks

    for pdf_path in pdf_files:
        with open(pdf_path, "rb") as f:
            reader = pypdf.PdfReader(f)
            total_pages = len(reader.pages)
            print(f"Processing {pdf_path.name} ({total_pages} pages) ...")
            for page_num, page in enumerate(reader.pages, start=1):
                print(f"  page {page_num}/{total_pages}", end="\r", flush=True)
                text = _markitdown_page(page)
                if not text:
                    continue
                for chunk in _chunk_words(text, chunk_size, overlap):
                    if chunk.strip():
                        chunks.append(
                            {
                                "text": chunk,
                                "source": pdf_path.name,
                                "page": page_num,
                            }
                        )

    return chunks
