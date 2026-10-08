import io
import json
import urllib.request
import pymupdf

def create_sample_timetable_pdf() -> bytes:
    """Create a sample timetable PDF with vector lines for pdfplumber table extraction."""
    doc = pymupdf.open()
    page = doc.new_page(width=792, height=612)  # Landscape letter
    
    # Title / Metadata
    page.insert_text((50, 40), "Department of Computer Science and Engineering", fontsize=16, fontname="helv")
    page.insert_text((50, 60), "Academic Year: 2025-2026 (Odd Semester) | Batch: General Shift | Class: CSE-A", fontsize=11, fontname="helv")
    
    # Timetable grid
    # Headers: Day, 09:00-10:00, 10:00-11:00, 11:15-12:15, 12:15-01:15, 02:00-03:00, 03:00-04:00
    headers = ["Day", "09:00 - 10:00", "10:00 - 11:00", "11:15 - 12:15", "12:15 - 01:15", "02:00 - 03:00", "03:00 - 04:00"]
    rows = [
        ["Monday", "CS101 (L301)\nDr. Alice Smith", "CS102 (L301)\nProf. Bob Jones", "CS103 (L301)\nDr. Carol White", "CS104 (L301)\nProf. David Lee", "CS105 (Lab 1)\nDr. Alice Smith", "CS105 (Lab 1)\nDr. Alice Smith"],
        ["Tuesday", "CS102 (L301)\nProf. Bob Jones", "CS101 (L301)\nDr. Alice Smith", "CS104 (L301)\nProf. David Lee", "CS103 (L301)\nDr. Carol White", "CS106 (L302)\nProf. Eva Green", "CS106 (L302)\nProf. Eva Green"],
        ["Wednesday", "CS103 (L301)\nDr. Carol White", "CS104 (L301)\nProf. David Lee", "CS101 (L301)\nDr. Alice Smith", "CS102 (L301)\nProf. Bob Jones", "Library", "Mentoring"]
    ]
    
    table_data = [headers] + rows
    
    x0, y0 = 50, 90
    col_w = [80, 100, 100, 100, 100, 100, 100]
    row_h = [30, 45, 45, 45]
    
    curr_y = y0
    for r_idx, row in enumerate(table_data):
        curr_x = x0
        h = row_h[r_idx]
        for c_idx, cell in enumerate(row):
            w = col_w[c_idx]
            rect = pymupdf.Rect(curr_x, curr_y, curr_x + w, curr_y + h)
            # Draw cell border
            page.draw_rect(rect, color=(0.2, 0.2, 0.2), width=1)
            # Insert text
            text_lines = cell.split("\n")
            line_y = curr_y + 14
            for line in text_lines:
                page.insert_text((curr_x + 5, line_y), line, fontsize=9 if r_idx > 0 else 10, fontname="helv")
                line_y += 12
            curr_x += w
        curr_y += h

    # Faculty allocation table below
    curr_y += 30
    page.insert_text((50, curr_y), "Course & Faculty Details:", fontsize=12, fontname="helv")
    curr_y += 15
    fac_headers = ["Code", "Subject Name", "Type", "Faculty Name", "Room"]
    fac_rows = [
        ["CS101", "Data Structures", "Theory", "Dr. Alice Smith", "L301"],
        ["CS102", "Operating Systems", "Theory", "Prof. Bob Jones", "L301"],
        ["CS103", "Database Systems", "Theory", "Dr. Carol White", "L301"],
        ["CS104", "Computer Networks", "Theory", "Prof. David Lee", "L301"],
        ["CS105", "Data Structures Lab", "Lab", "Dr. Alice Smith", "Lab 1"],
        ["CS106", "Web Development", "Theory", "Prof. Eva Green", "L302"]
    ]
    
    fac_table_data = [fac_headers] + fac_rows
    fac_col_w = [70, 160, 70, 160, 70]
    fac_row_h = 22
    
    for r_idx, row in enumerate(fac_table_data):
        curr_x = 50
        for c_idx, cell in enumerate(row):
            w = fac_col_w[c_idx]
            rect = pymupdf.Rect(curr_x, curr_y, curr_x + w, curr_y + fac_row_h)
            page.draw_rect(rect, color=(0.3, 0.3, 0.3), width=0.8)
            page.insert_text((curr_x + 5, curr_y + 15), cell, fontsize=9, fontname="helv")
            curr_x += w
        curr_y += fac_row_h

    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes

if __name__ == "__main__":
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

    from app.services.document_constraints import extract_pdf_tables_and_text
    from app.api.endpoints.imports import ACADEMIC_EXTRACTOR_SYSTEM_PROMPT

    pdf_bytes = create_sample_timetable_pdf()
    print(f"1. Created sample timetable PDF ({len(pdf_bytes)} bytes)")

    print("\n2. Running extract_pdf_tables_and_text...")
    extracted_text, warnings = extract_pdf_tables_and_text(pdf_bytes)
    print(f"Extracted {len(extracted_text)} characters. Warnings: {warnings}")
    print("\n--- Extracted Table Preview ---")
    print(extracted_text[:1200])
    print("--- End Preview ---\n")

    print("3. Querying Ollama (qwen3:1.7b) with extracted table text (Streaming)...")
    prompt = (
        "Extract ONLY the academic entities that are explicitly and literally present in the following timetable table and text. "
        "Respond IMMEDIATELY with the JSON object. Do NOT think, do NOT reason, do NOT include <think> tags. Start directly with '{' and end with '}'. "
        "If a field (email, code, section, department, batch, room, etc.) is not clearly stated in the text, set it to \"\" or null. "
        "Return ONLY a valid JSON object matching the required schema with no extra commentary.\n\n"
        f"{extracted_text}"
    )

    req_data = json.dumps({
        "model": "qwen3:1.7b",
        "stream": True,
        "temperature": 0.0,
        "max_tokens": 2048,
        "messages": [
            {"role": "system", "content": "You are a direct data extractor. Output only the JSON object, absolutely no internal thought, reasoning, or explanation. Start directly with '{'."},
            {"role": "user", "content": prompt}
        ],
        "response_format": {"type": "json_object"}
    }).encode("utf-8")

    req = urllib.request.Request(
        "http://localhost:11434/v1/chat/completions",
        data=req_data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    content = ""
    with urllib.request.urlopen(req, timeout=180) as resp:
        for line in resp:
            line_str = line.decode("utf-8").strip()
            if not line_str or line_str == "data: [DONE]":
                continue
            if line_str.startswith("data: "):
                line_str = line_str[6:]
            try:
                chunk = json.loads(line_str)
                delta = chunk.get("choices", [{}])[0].get("delta", {})
                tok = delta.get("content", "")
                if tok:
                    content += tok
                    sys.stdout.write(tok)
                    sys.stdout.flush()
            except Exception:
                pass

    print("\n\nFinished streaming.")
    import re
    cleaned_content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()
    cleaned_content = re.sub(r'^```(?:json)?\s*', '', cleaned_content).strip()
    cleaned_content = re.sub(r'\s*```$', '', cleaned_content).strip()
    
    parsed = json.loads(cleaned_content)
    print("4. Successfully parsed JSON from Qwen3:1.7B:")
    print(json.dumps(parsed, indent=2))
    
    # Assertions
    assert len(parsed.get("subjects", [])) > 0, "Subjects should be extracted"
    assert len(parsed.get("faculty", [])) > 0, "Faculty should be extracted"
    print("\nAll pipeline assertions PASSED successfully!")

