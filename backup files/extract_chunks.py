# extract_chunks.py
import json
from docx import Document
from pathlib import Path

# Get project root (parent of backend directory)
BACKEND_DIR = Path(__file__).parent
PROJECT_ROOT = BACKEND_DIR.parent
DATA_DIR = PROJECT_ROOT / "data"

INPUT_DOCX = DATA_DIR / "QuotePlan.docx"  # Read from data folder
OUTPUT_JSON = DATA_DIR / "chunks.json"  # Write to data folder
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
    # Ensure data directory exists
    DATA_DIR.mkdir(exist_ok=True)
    
    if not INPUT_DOCX.exists():
        print(f"Put your DOCX at: {INPUT_DOCX.resolve()}")
        raise SystemExit(1)

    chunks = docx_to_chunks(INPUT_DOCX)
    print("Created chunks:", len(chunks))
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)
    print("Wrote", OUTPUT_JSON)
