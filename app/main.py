from fastapi import FastAPI
from app.routes import documents
from app.core.masking import load_spacy_model

app = FastAPI(title="Reversible PDF Masking API")

@app.on_event("startup")
async def startup_event():
    """Load the spaCy model on application startup."""
    print("Loading spaCy model...")
    load_spacy_model()
    print("spaCy model loaded successfully.")

app.include_router(documents.router, prefix="/documents", tags=["documents"])

@app.get("/")
def read_root():
    return {"message": "Welcome to the Reversible PDF Masking API"}