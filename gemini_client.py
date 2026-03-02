import json
import time
import logging
import os
from pathlib import Path
from google import genai
from google.genai import types

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def _load_env_file(env_name: str = ".env") -> None:
  env_path = Path(__file__).resolve().with_name(env_name)
  if not env_path.exists():
    return

  for raw_line in env_path.read_text().splitlines():
    line = raw_line.strip()
    if not line or line.startswith("#") or "=" not in line:
      continue
    key, value = line.split("=", 1)
   
    os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_env_file()

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
  raise RuntimeError("Missing GEMINI_API_KEY. Set it in your environment or .env file.")

client = genai.Client(api_key=api_key)

def get_page_data(image_content, page_num):

    models_to_try = ["gemini-3-flash-preview", "gemini-2.5-flash", "gemini-1.5-flash"]
    

    prompt = f"""
Extract all table data from this image (Section {page_num}). 
You must normalize the output into a generic column format.

Return ONLY a valid JSON object with this exact structure:
{{
  "header_map": {{
    "Col 1": "Actual Header Name from Image",
    "Col 2": "Actual Header Name from Image",
    ...
  }},
  "rows": [
    {{
      "Col 1": "Value 1",
      "Col 2": "Value 2",
      ...
    }}
  ]
}}

Rules:
1. Every row must use the keys "Col 1", "Col 2", etc.
2. The "header_map" must contain the original names found in the image.
3. If no table is found, return {{"header_map": {{}}, "rows": []}}.
Do not include any conversational text or markdown blocks.
"""

    for model_id in models_to_try:
        try:
           
            time.sleep(12) 
            
            logger.info(f"Attempting extraction with {model_id}...")

            response = client.models.generate_content(
                model=model_id,
                contents=[
                    prompt, 
                    types.Part.from_bytes(data=image_content, mime_type="image/jpeg")
                ]
            )
            
            if response and response.text:
              
                clean_text = response.text.strip()
                if clean_text.startswith("```"):
                    clean_text = clean_text.split("\n", 1)[1].rsplit("\n", 1)[0].strip()
                
                return json.loads(clean_text)

        except Exception as e:
            if "404" in str(e):
                logger.warning(f"{model_id} not found, trying next model...")
                continue 
            logger.error(f"Error with {model_id}: {e}")
           
            if "429" in str(e):
                time.sleep(60)
                return get_page_data(image_content, page_num)
            
    return None