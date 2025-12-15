# extract_chunks.py
import json
from docx import Document
from pathlib import Path

INPUT_DOCX = r"D:\qdrant-rag\Quote Plan Help Manual.docx"  # put file in same folder
OUTPUT_JSON = "chunks.json"
CHUNK_SIZE_CHARS = 800  # adjust if you want larger/smaller chunks

def docx_to_chunks(path):
    doc = Document(path)
    chunks = []
    current = ""

    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            # treat blank line as paragraph break
            if current:
                chunks.append(current.strip())
                current = ""
            continue

        if len(current) + len(text) + 1 <= CHUNK_SIZE_CHARS:
            current = (current + " " + text).strip()
        else:
            if current:
                chunks.append(current.strip())
            current = text

    if current:
        chunks.append(current.strip())

    return chunks

if __name__ == "__main__":
    p = Path(INPUT_DOCX)
    if not p.exists():
        print(f"Put your DOCX at: {p.resolve()}")
        raise SystemExit(1)

    chunks = docx_to_chunks(p)
    print("Created chunks:", len(chunks))
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)
    print("Wrote", OUTPUT_JSON)
