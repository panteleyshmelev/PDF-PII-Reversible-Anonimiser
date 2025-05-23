from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig
import spacy
import spacy_curated_transformers  # <-- ADD THIS LINE
from spacy.cli.download import download as spacy_download

def load_spacy_model(model_name: str = "en_core_web_trf"):
    """Loads the spaCy model, downloading it if necessary."""
    try:
        spacy.load(model_name)
    except OSError:
        print(f"spaCy model '{model_name}' not found. Downloading...")
        spacy_download(model_name)
        spacy.load(model_name)
    return spacy.load(model_name)

# Initialize Presidio components
analyzer = AnalyzerEngine()
anonymizer = AnonymizerEngine()

def get_pii_entities(text: str):
    """Detects PII entities in the given text."""
    return analyzer.analyze(text=text, language='en')

def get_anonymized_text(text: str, pii_entities):
    """Anonymizes the text based on detected PII entities."""
    return anonymizer.anonymize(
        text=text,
        analyzer_results=pii_entities,
        operators={"DEFAULT": OperatorConfig("replace", {"new_value": "<MASKED>"})}
    )