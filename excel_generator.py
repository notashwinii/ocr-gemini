import pandas as pd
import json
import os

def save_outputs(results):
    """
    Standardizes generic Col 1, Col 2 keys using the AI-provided header_map.
    Saves to /tmp/ for Vercel compatibility.
    """
    all_data = []
    final_header_map = {}

    for section in results:
        if not section or not isinstance(section, dict):
            continue
            
        section_headers = section.get("header_map", {})
        final_header_map.update(section_headers)
        
        # Collect the rows
        rows = section.get("rows", [])
        if isinstance(rows, list):
            all_data.extend(rows)

    if not all_data:
        print("No data extracted.")
        return


    json_path = "/tmp/output.json"
    xlsx_path = "/tmp/output.xlsx"

    # 1. Save JSON
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(all_data, f, ensure_ascii=False, indent=4)

    # 2. Save Excel
    try:
        df = pd.DataFrame(all_data)
        
     
        if final_header_map:
         
            existing_map = {k: v for k, v in final_header_map.items() if k in df.columns}
            df.rename(columns=existing_map, inplace=True)
            
        df.to_excel(xlsx_path, index=False)
        print(f"Successfully saved to {xlsx_path} with {len(all_data)} rows.")
    except Exception as e:
        print(f"Excel Error: {e}")