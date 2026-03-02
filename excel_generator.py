import pandas as pd
import json
import os

def save_outputs(results):
    """
    Standardizes generic Col 1, Col 2 keys using the AI-provided header_map.
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

    # 1. Save JSON
    with open("output.json", "w", encoding="utf-8") as f:
        json.dump(all_data, f, ensure_ascii=False, indent=4)

    # 2. Save Excel
    try:
        df = pd.DataFrame(all_data)
        
        # Rename "Col 1" -> "Original Name" using the header_map
        if final_header_map:
            df.rename(columns=final_header_map, inplace=True)
            
        df.to_excel("output.xlsx", index=False)
        print(f"Successfully saved {len(all_data)} rows with dynamic headers.")
    except Exception as e:
        print(f"Excel Error: {e}")