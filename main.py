import uvicorn
import sys
import os
import signal
import shutil
import fitz  # PyMuPDF
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

# Import your custom logic
from gemini_client import get_page_data
from excel_generator import save_outputs

app = FastAPI()

# --- 1. SETUP DIRECTORIES ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")

os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(UPLOADS_DIR, exist_ok=True)

# Mount static files (for CSS/JS access)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# --- 2. SIGNAL HANDLING (For Ctrl+C) ---
def handle_exit(sig, frame):
    print("\n[!] Ctrl+C detected. Shutting down server gracefully...")
    sys.exit(0)

signal.signal(signal.SIGINT, handle_exit)

# --- 3. ROUTES ---

@app.get("/")
async def read_index():
    """Serves the frontend UI."""
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"error": "index.html not found in /static folder. Please create it."}

@app.post("/process")
async def process_endpoint(file: UploadFile = File(...), pages: str = Form("1-1")):
    """Handles PDF upload, quadrant splitting, and Gemini extraction."""
    temp_pdf = os.path.join(UPLOADS_DIR, file.filename)
    
    # Save uploaded file
    with open(temp_pdf, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    doc = None
    try:
        doc = fitz.open(temp_pdf)
        # Parse range (e.g., "1-3")
        start_str, end_str = pages.split('-')
        start, end = int(start_str), int(end_str)
        
        all_results = []

        # Process requested pages
        for p_idx in range(start - 1, min(end, len(doc))):
            page = doc.load_page(p_idx)
            rect = page.rect
            h_step = rect.y1 / 4  # Divide into 4 horizontal sections

            sections = [
                fitz.Rect(0, 0, rect.x1, h_step),                # Section 1
                fitz.Rect(0, h_step, rect.x1, h_step * 2),        # Section 2
                fitz.Rect(0, h_step * 2, rect.x1, h_step * 3),    # Section 3
                fitz.Rect(0, h_step * 3, rect.x1, rect.y1)         # Section 4
            ]

            for i, section_rect in enumerate(sections, 1):
                print(f"--> Processing Page {p_idx + 1} | Section {i}/4...")
                
                # Render quadrant at 2x zoom for OCR clarity
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), clip=section_rect)
                img_bytes = pix.tobytes("jpeg")
                
                # Call Gemini Client
                page_data = get_page_data(img_bytes, f"P{p_idx+1}_S{i}")
                if page_data:
                    all_results.append(page_data)

        # Generate output files
        save_outputs(all_results)
        
        return {
            "message": "Extraction Successful",
            "json_url": "/download/json",
            "xlsx_url": "/download/xlsx"
        }

    except Exception as e:
        print(f"Server Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if doc:
            doc.close()
        if os.path.exists(temp_pdf):
            os.remove(temp_pdf)

@app.get("/download/{file_type}")
async def download(file_type: str):
    """Provides the generated Excel/JSON files for download."""
    file_map = {"json": "output.json", "xlsx": "output.xlsx"}
    filename = file_map.get(file_type)
    if filename and os.path.exists(filename):
        return FileResponse(filename, filename=filename)
    raise HTTPException(status_code=404, detail="File not found. Process a PDF first.")

# --- 4. EXECUTION ---
if __name__ == "__main__":
    print("Starting FastAPI server on http://127.0.0.1:8000")
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")