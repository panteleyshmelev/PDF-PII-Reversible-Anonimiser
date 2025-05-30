from fastapi import FastAPI
# from app.routes import documents # Old router
from app.routes import documents as text_processing_router # Assuming you kept the filename documents.py
from app.core.masking import load_spacy_model

app = FastAPI(title="Text PII Masking API") # Updated title

@app.on_event("startup")
async def startup_event():
    print("Loading spaCy model...")
    load_spacy_model()
    print("spaCy model loaded successfully.")

# app.include_router(documents.router, prefix="/documents", tags=["documents"]) # Old
app.include_router(text_processing_router.router, prefix="/text", tags=["Text Processing"]) # New

@app.get("/")
def read_root():
    return {"message": "Welcome to the Text PII Masking API"}