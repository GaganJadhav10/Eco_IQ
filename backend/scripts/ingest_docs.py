"""Index source documents (PDF or text) into the ChromaDB `doc_chunks` collection.

Usage:  python scripts/ingest_docs.py            (reads backend/data/sources/)
        python scripts/ingest_docs.py --clear    (drops the collection first)

File naming: name each file after its `sources.csv` id, e.g. `srinivasarao_2013.pdf`, so every chunk
keeps a real source id and page number. Files whose name matches no source id are still indexed, with
the filename as the source id.

This is optional. With no documents present the system behaves exactly as before: mechanism passages
come from the curated relationship records instead.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.retrieval.chroma_store import ChromaStore  # noqa: E402
from app.retrieval.store import parse_sources  # noqa: E402

DOCS_DIR = ROOT / "data" / "sources"
CHUNK_CHARS = 1200
OVERLAP = 150


def read_pdf(path: Path) -> list[tuple[int, str]]:
    try:
        from pypdf import PdfReader
    except ImportError:
        sys.exit("pypdf is required for PDFs: pip install pypdf")
    reader = PdfReader(str(path))
    return [(i + 1, page.extract_text() or "") for i, page in enumerate(reader.pages)]


def chunk(pages: list[tuple[int, str]]) -> list[tuple[int, str]]:
    out = []
    for page_no, text in pages:
        text = " ".join(text.split())
        if len(text) < 80:
            continue  # scanned page or near-empty
        start = 0
        while start < len(text):
            out.append((page_no, text[start:start + CHUNK_CHARS]))
            start += CHUNK_CHARS - OVERLAP
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--clear", action="store_true", help="drop existing document chunks first")
    ap.add_argument("--dir", default=str(DOCS_DIR))
    args = ap.parse_args()

    docs_dir = Path(args.dir)
    docs_dir.mkdir(parents=True, exist_ok=True)
    files = sorted(p for p in docs_dir.iterdir() if p.suffix.lower() in (".pdf", ".txt", ".md"))
    if not files:
        print(f"No documents in {docs_dir}. Drop PDFs named after their source id "
              f"(e.g. ipcc_srccl_2019.pdf) and run again.")
        return

    store = ChromaStore()
    if args.clear:
        store.clear_docs()
    known = {s.id for s in parse_sources()}

    total = 0
    for path in files:
        source_id = path.stem if path.stem in known else path.stem
        if path.stem not in known:
            print(f"  ! {path.name}: no matching id in sources.csv, indexing under '{source_id}'")
        pages = read_pdf(path) if path.suffix.lower() == ".pdf" else [(1, path.read_text(encoding="utf-8"))]
        chunks = chunk(pages)
        if not chunks:
            print(f"  ! {path.name}: no extractable text (scanned image?), skipped")
            continue
        store.add_doc_chunks(source_id, chunks)
        total += len(chunks)
        print(f"  + {path.name}: {len(chunks)} chunks from {len(pages)} pages")

    print(f"Indexed {total} chunks. doc_chunks now holds {store.doc_chunk_count()}.")


if __name__ == "__main__":
    main()
