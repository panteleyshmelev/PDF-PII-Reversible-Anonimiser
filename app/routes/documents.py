import uuid
import json
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from app.core import pdf_processor, masking
import os
import fitz
from collections import defaultdict

router = APIRouter()

UPLOAD_DIR = "data/uploads"
MASKED_DIR = "data/masked_pdfs"
UNMASKED_DIR = "data/unmasked_pdfs"
MAPPING_FILE = "data/masking_maps.json"

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(MASKED_DIR, exist_ok=True)
os.makedirs(UNMASKED_DIR, exist_ok=True)

def load_mappings():
    if os.path.exists(MAPPING_FILE):
        try:
            with open(MAPPING_FILE, "r") as f:
                content = f.read()
                if not content:
                    return {}
                return json.loads(content)
        except json.JSONDecodeError:
            return {}
    return {}

def save_mappings(mappings):
    with open(MAPPING_FILE, "w") as f:
        json.dump(mappings, f, indent=4)

@router.post("/mask")
async def mask_document(file: UploadFile = File(...)):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed.")

    file_id = str(uuid.uuid4())
    upload_path = os.path.join(UPLOAD_DIR, f"{file_id}.pdf")
    masked_path = os.path.join(MASKED_DIR, f"masked_{file_id}.pdf")

    with open(upload_path, "wb") as buffer:
        buffer.write(await file.read())

    doc = fitz.open(upload_path)
    full_text = "".join([page.get_text() for page in doc])
    doc.close()

    pii_entities_raw = masking.get_pii_entities(full_text)

    # --- REFINED ENTITY FILTERING LOGIC ---
    # Sort entities: first by start position, then by end position descending (longest first)
    # This ensures that if "Bobby Lim" and "Bobby" start at the same char, "Bobby Lim" comes first.
    pii_entities_raw.sort(key=lambda e: (e.start, -e.end))
    
    filtered_entities = []
    for current_entity in pii_entities_raw:
        is_subset_of_already_kept_entity = False
        # Check if current_entity is a subset of any entity *already chosen* in filtered_entities
        for kept_entity in filtered_entities:
            if current_entity.start >= kept_entity.start and \
               current_entity.end <= kept_entity.end:
                # current_entity is fully contained within or identical to a kept_entity
                is_subset_of_already_kept_entity = True
                break  # No need to check further against other kept_entities
        
        if not is_subset_of_already_kept_entity:
            filtered_entities.append(current_entity)
    # --- END OF REFINED ENTITY FILTERING LOGIC ---

    # Create unique placeholders for each unique piece of PII text from the filtered list
    pdf_replacements = {}
    unmasking_map = {}
    counters = defaultdict(int)
    
    # We iterate through the filtered entities. For each *unique text span* from these,
    # we create one placeholder.
    # This uses a dictionary comprehension to effectively get unique text spans first.
    unique_texts_and_types = {}
    for entity in filtered_entities:
        original_text = full_text[entity.start:entity.end]
        # If we encounter the same text span multiple times (e.g. "Bobby Lim" appears twice in doc),
        # we only care about its first encountered entity type for placeholder generation.
        if original_text not in unique_texts_and_types:
            unique_texts_and_types[original_text] = entity.entity_type
    
    for original_text, entity_type in unique_texts_and_types.items():
        count = counters[entity_type]
        placeholder = f"<{entity_type}_{count}>"
        pdf_replacements[original_text] = placeholder
        unmasking_map[placeholder] = original_text
        counters[entity_type] += 1

    all_mappings = load_mappings()
    all_mappings[file_id] = unmasking_map
    save_mappings(all_mappings)

    # The pdf_processor.py (with longest-string-first replacement) will handle
    # replacing "Bobby Lim" before "Bobby" if both exist as separate entries in pdf_replacements
    pdf_processor.replace_text_in_pdf(upload_path, masked_path, pdf_replacements)

    return {"file_id": file_id, "masked_file_path": masked_path, "detail": "Document masked successfully with robust de-duplication."}


@router.get("/unmask/{file_id}")
async def unmask_document(file_id: str):
    masked_path = os.path.join(MASKED_DIR, f"masked_{file_id}.pdf")
    if not os.path.exists(masked_path):
        raise HTTPException(status_code=404, detail="Masked file not found.")

    all_mappings = load_mappings()
    if file_id not in all_mappings:
        raise HTTPException(status_code=404, detail="Mapping for this file not found.")

    unmask_map = all_mappings[file_id]
    unmasked_path = os.path.join(UNMASKED_DIR, f"unmasked_{file_id}.pdf")

    pdf_processor.replace_text_in_pdf(masked_path, unmasked_path, unmask_map)

    return FileResponse(unmasked_path, media_type='application/pdf', filename=f"unmasked_{file_id}.pdf")
    