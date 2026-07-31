"""
ExFlow Enterprise — OCR Invoice Scanner
=========================================
Extract text from invoice images using Tesseract or fallback.
"""
import os, sys
sys.path = [p for p in sys.path if 'hermes' not in p.lower()]

import re, tempfile, subprocess
from datetime import datetime

# PIL imported lazily inside functions to avoid Hermes venv conflict

# Try importing pytesseract
try:
    import pytesseract
    HAS_TESSERACT = True
except ImportError:
    HAS_TESSERACT = False

# Try importing easyocr as fallback
try:
    import easyocr
    HAS_EASYOCR = True
except ImportError:
    HAS_EASYOCR = False

def check_tesseract():
    """Check if tesseract is installed on the system."""
    try:
        subprocess.run(["tesseract", "--version"], capture_output=True, check=True)
        return True
    except (subprocess.SubprocessError, FileNotFoundError):
        return False

def preprocess_image(img_path):
    """Enhance image for better OCR results."""
    from PIL import Image, ImageEnhance
    img = Image.open(img_path)
    # Convert to grayscale
    img = img.convert("L")
    # Increase contrast
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(2.0)
    # Save preprocessed
    out_path = img_path + "_processed.png"
    img.save(out_path)
    return out_path

def extract_from_image(img_path, lang="deu+eng"):
    """
    Extract text from an invoice image.
    Returns: dict with {text, amount, date, vendor, items}
    """
    result = {"text": "", "amount": 0.0, "date": None, "vendor": "", "items": [],
              "confidence": 0, "method": ""}
    
    # Try pytesseract first
    if HAS_TESSERACT and check_tesseract():
        try:
            processed = preprocess_image(img_path)
            text = pytesseract.image_to_string(processed, lang=lang)
            result["text"] = text
            result["method"] = "tesseract"
            # Parse
            _parse_invoice_data(result)
            return result
        except Exception:
            pass
    
    # Try easyocr
    if HAS_EASYOCR:
        try:
            reader = easyocr.Reader(["de", "en"], gpu=False)
            raw = reader.readtext(img_path)
            text = "\n".join([item[1] for item in raw])
            conf = sum(item[2] for item in raw) / max(len(raw), 1)
            result["text"] = text
            result["confidence"] = int(conf * 100)
            result["method"] = "easyocr"
            _parse_invoice_data(result)
            return result
        except Exception:
            pass
    
    # No OCR available
    result["text"] = "⚠️ No OCR engine available. Install: pip install pytesseract && brew install tesseract"
    result["method"] = "none"
    return result

def _parse_invoice_data(result):
    """Parse extracted text for invoice fields."""
    text = result.get("text", "")
    
    # Extract total amount
    patterns = [
        r'(?:Total|Summe|Sum|مبلغ|جمع|Preis|Betrag|Amount|Gesamt)\s*:?\s*([\d.,]+)\s*(?:€|EUR|EUR)',
        r'([\d.,]+)\s*(?:€|EUR|EUR)\s*(?:Total|Summe|Gesamt)',
        r'(?:Betrag|Amount|مبلغ)\s*:?\s*([\d.,]+)\s*(?:€|EUR|EUR)',
        r'([\d.,]+)\s*(?:€|EUR)',  # any number followed by euro sign
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            try:
                amount_str = m.group(1).strip()
                # Handle "5,00" (German format with comma as decimal)
                if ',' in amount_str and amount_str.count(',') == 1 and amount_str.count('.') == 0:
                    amount_str = amount_str.replace(',', '.')
                # Handle "500,00" or "5.000,00" (German format)
                elif ',' in amount_str:
                    amount_str = amount_str.replace('.', '').replace(',', '.')
                # Handle "5.00" (standard format with dot)
                else:
                    amount_str = amount_str.replace(',', '')
                result["amount"] = float(amount_str)
                break
            except ValueError:
                pass
    
    # Extract date
    date_patterns = [
        r'(\d{2}\.\d{2}\.\d{4})',
        r'(\d{4}-\d{2}-\d{2})',
        r'(\d{2}/\d{2}/\d{4})',
        r'(\d{2}\.\d{2}\.\d{2})',
    ]
    for p in date_patterns:
        m = re.search(p, text)
        if m:
            result["date"] = m.group(1)
            break
    
    # Extract vendor name (often first non-empty line)
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    if lines:
        # Skip common non-vendor first lines
        skip_words = ["rechnung", "invoice", "facture", "date", "datum", "bill", "receipt"]
        for line in lines[:5]:
            if len(line) > 5 and not any(s in line.lower() for s in skip_words):
                result["vendor"] = line
                break

    # Extract line items (simple approach)
    for line in lines:
        m = re.search(r'([\d.,]+)\s*(?:€|EUR)\s*$', line)
        if m and not any(x in line.lower() for x in ["total", "summe", "sum", "مبلغ", "ust", "mwst", "steuer"]):
            try:
                amt = float(m.group(1).replace(".", "").replace(",", "."))
                desc = re.sub(r'[\d.,\s€EUR]+$', '', line).strip()
                result["items"].append({"description": desc, "amount": amt})
            except ValueError:
                pass

    return result

if __name__ == "__main__":
    # Test with a sample file if provided
    import sys
    if len(sys.argv) > 1:
        r = extract_from_image(sys.argv[1])
        print(f"Method: {r['method']}")
        print(f"Vendor: {r['vendor']}")
        print(f"Amount: {r['amount']}€")
        print(f"Date: {r['date']}")
        print(f"Items: {len(r['items'])}")
        print(f"Confidence: {r['confidence']}%")
        print(f"Text:\n{r['text'][:500]}")
    else:
        print("OCR module loaded. Usage: python ocr_scanner.py <image_path>")
