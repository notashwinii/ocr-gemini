import os
import io
import fitz  
import logging
import cloudinary
import cloudinary.uploader
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

# Import your custom logic
from gemini_client import get_page_data
from excel_generator import save_outputs

# --- 1. CONFIGURE LOGGING ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler()] # Essential for Vercel logs
)
logger = logging.getLogger("fastapi-ocr")

app = FastAPI()

# Cloudinary Config
cloudinary.config(
    cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key = os.getenv("CLOUDINARY_API_KEY"),
    api_secret = os.getenv("CLOUDINARY_API_SECRET"),
    secure = True
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/")
async def read_index():
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    logger.error("index.html not found in static directory")
    return {"error": "index.html not found"}

@app.post("/process")
async def process_endpoint(file: UploadFile = File(...), pages: str = Form("1-1")):
    doc = None
    logger.info(f"Received file: {file.filename}, Page range: {pages}")
    
    try:
        pdf_bytes = await file.read()
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        
        start_str, end_str = pages.split('-')
        start, end = int(start_str), int(end_str)
        
        all_results = []

        for p_idx in range(start - 1, min(end, len(doc))):
            logger.info(f"Processing PDF Page {p_idx + 1}")
            page = doc.load_page(p_idx)
            rect = page.rect
            
            mid_y = rect.y1 / 2
            sections = [
                fitz.Rect(0, 0, rect.x1, mid_y),    
                fitz.Rect(0, mid_y, rect.x1, rect.y1)
            ]

            for i, section_rect in enumerate(sections, 1):
                logger.info(f"Rendering Section {i} of Page {p_idx + 1}")
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), clip=section_rect)
                img_bytes = pix.tobytes("jpeg")
              
                # Cloudinary Upload
                logger.info(f"Uploading Section {i} to Cloudinary...")
                upload_result = cloudinary.uploader.upload(img_bytes)
                image_url = upload_result.get("url")
                
                # Gemini OCR
                logger.info(f"Sending Section {i} to Gemini Client...")
                page_data = get_page_data(img_bytes, f"P{p_idx+1}_S{i}")
                
                if page_data: 
                    page_data['cloud_url'] = image_url
                    all_results.append(page_data)

        logger.info(f"Extraction complete. Saving outputs for {len(all_results)} sections.")
        save_outputs(all_results)
        
        return {
            "message": "Extraction Successful",
            "results_count": len(all_results),
            "json_url": "/download/json",
            "xlsx_url": "/download/xlsx"
        }

    except Exception as e:
        logger.exception("Fatal error during processing") # Captures the whole traceback
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if doc:
            doc.close()

@app.get("/download/{file_type}")
async def download(file_type: str):
    file_map = {"json": "/tmp/output.json", "xlsx": "/tmp/output.xlsx"}
    path = file_map.get(file_type)
    
    if path and os.path.exists(path):
        logger.info(f"Serving download: {path}")
        return FileResponse(path, filename=os.path.basename(path))
    
    logger.warning(f"Download failed: {file_type} not found at {path}")
    raise HTTPException(status_code=404, detail="File not found.")

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting local development server...")
    uvicorn.run(app, host="127.0.0.1", port=8000)