import time
import subprocess
import sys
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Get project root and paths
BACKEND_DIR = Path(__file__).parent
PROJECT_ROOT = BACKEND_DIR.parent
DATA_DIR = PROJECT_ROOT / "data"
WATCH_PATH = str(DATA_DIR)  # Watch data folder for document changes

class DocChangeHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if event.src_path.endswith((".docx", ".pdf", ".txt")):
            print("📄 Documentation changed. Re-ingesting...")
            self.run_pipeline()

    def run_pipeline(self):
        # Change to backend directory to run scripts
        extract_script = BACKEND_DIR / "extract_chunks.py"
        ingest_script = BACKEND_DIR / "ingest_qdrant.py"
        
        subprocess.run([sys.executable, str(extract_script)], cwd=str(PROJECT_ROOT))
        subprocess.run([sys.executable, str(ingest_script)], cwd=str(PROJECT_ROOT))
        print("✅ Knowledge base updated")

if __name__ == "__main__":
    event_handler = DocChangeHandler()
    observer = Observer()
    observer.schedule(event_handler, WATCH_PATH, recursive=True)
    observer.start()

    print("👀 Watching for documentation changes...")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()