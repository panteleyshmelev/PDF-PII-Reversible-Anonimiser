import fitz  # PyMuPDF
from typing import Dict

def replace_text_in_pdf(
    pdf_path: str,
    output_pdf_path: str,
    replacements: Dict[str, str]
):
    """
    Finds and replaces multiple text instances in a PDF using redaction annotations.
    It processes replacements in order of text length (longest first) and
    applies redactions iteratively on each page after each word type is processed
    to avoid substring conflicts.
    """
    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        print(f"Error opening PDF '{pdf_path}': {e}")
        return

    modified_overall = False
    
    # Sort keys by length, descending, to ensure "Bobby Lim" is replaced before "Bobby"
    sorted_keys = sorted(replacements.keys(), key=len, reverse=True)

    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        page_was_modified_in_this_pass = False

        # Loop through the sorted keys for replacement
        for word_to_find in sorted_keys:
            replacement_word = replacements[word_to_find]
            
            instances = page.search_for(word_to_find)
            if instances:
                modified_overall = True
                page_was_modified_in_this_pass = True
                for inst_rect in instances:
                    page.add_redact_annot(inst_rect, text=replacement_word, fill=(1, 1, 1))
                
                # --- KEY CHANGE: Apply redactions for THIS word immediately ---
                page.apply_redactions() 
                # Reload the page to ensure subsequent searches see the redacted content
                # This is important because apply_redactions() modifies the page stream
                if page_num < len(doc) -1 : # Check if it's not the last page
                    doc.load_page(page_num) # Reload the page
                # For the last page, it might not be necessary or could error if doc is closed.
                # However, PyMuPDF handles page reloads internally quite well.
                # A safer way to ensure context is fresh if many redactions are applied
                # might be to fully save and reopen, but that's too slow.
                # Let's stick with applying and assuming the page object updates or re-searching works on modified.
                # Re-evaluating: `page.apply_redactions()` modifies the page. Subsequent `page.search_for()`
                # on the *same page object* will search the now-modified content.
                # So, reloading the page instance might not even be needed here. Let's test without it first.
                # The PyMuPDF docs state: "Page content will change by this command."

        # No, applying after each word_to_find is the way. The above comment block was me overthinking.
        # The simple loop and apply_redactions() inside `if instances:` is correct.

    # The loop structure should be:
    # for page:
    #   for word_to_find (sorted):
    #     if page.search_for(word_to_find):
    #       add_redact_annots
    #       page.apply_redactions() # <---- THIS IS THE KEY
    #
    # Let's re-write the loop structure cleanly.

    for page in doc: # Iterate through each page
        # For each page, iterate through the words to find, longest first
        for word_to_find in sorted_keys:
            replacement_word = replacements[word_to_find]
            
            instances = page.search_for(word_to_find)
            if instances:
                modified_overall = True
                for inst_rect in instances:
                    page.add_redact_annot(inst_rect, text=replacement_word, fill=(1, 1, 1))
                
                # Apply redactions for THIS SPECIFIC word_to_find on THIS page immediately
                # This "burns in" the redaction, so subsequent searches for shorter substrings
                # will not find them within the already redacted text.
                page.apply_redactions() 

    if modified_overall:
        doc.save(output_pdf_path, garbage=3, deflate=True, clean=True)
        print(f"Successfully processed and saved the modified PDF to '{output_pdf_path}'")
    else:
        # If no modifications were made overall, we might just copy the file
        # or save it normally if an empty save is desired.
        # For simplicity, we'll just print.
        print("No text replacements were made in the document.")
        # To ensure an output file is always created, even if no changes:
        # doc.save(output_pdf_path, garbage=3, deflate=True, clean=True)


    doc.close()