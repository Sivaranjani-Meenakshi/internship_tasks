import fitz # PyMuPDF
import pdfplumber
import json,sys
from datetime import datetime
from config_loader import load_config
config=load_config()

def log_exception(e, func_name, logfile=config["LOG_FILE"]):
    try:
        exc_type, exc_obj, tb = sys.exc_info()
        lineno = tb.tb_lineno if tb else "N/A"
        error_message = f"\n[{datetime.now()} In {func_name} LINE.NO-{lineno} : {exc_obj} error {e}"
        print(error_message)
        with open(logfile, 'a', encoding='utf-8') as fp:
            fp.writelines(error_message + "\n")
    except Exception as ee:
        print("Logging failed:", ee)

# --------------- 1a. Extract text using fitz -------------

def extract_text_fitz(pdf_path):
    try:
        doc = fitz.open(pdf_path)
        pages = []
        for page_num, page in enumerate(doc, start=1):
            text = page.get_text("text")
            if text.strip():
                paragraphs = text.split("\n")
            else:
                paragraphs = [""]  # empty page → return ""
            pages.append({"page": page_num, "paragraphs": paragraphs})
        return pages
    except Exception as e:
        log_exception(e, "extract_text_fitz")
        return []


# ------------- 1b. Extract text using pdfplumber ---------------
# -----------------------------
def extract_text_pdfplumber(pdf_path):
    try:
        pages = []
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                text = page.extract_text(regex=True)
                if text and text.strip():
                    paragraphs = text.replace("\n"," ")
                else:
                    paragraphs = [""]  # empty page → return ""
                pages.append({"page": page_num, "paragraphs": paragraphs})
        return pages
    except Exception as e:
        log_exception(e, "extract_text_pdfplumber")
        return []


# -------------- 2. Extract text + coordinates ----------------

def extract_text_with_coordinates(pdf_path):
    try:
        with pdfplumber.open(pdf_path) as pdf:
            pages=[]
            for page_num, page in enumerate( pdf.pages,start=1):
                content=page.extract_words()
                for word in content:
                    bbox = (round(word['x0'],2),
                            round(word['top'],2),
                            round(word['x1'],2),
                            round(word['bottom'],2))
                    file={"text":str(word['text']),"bbox":str(bbox)}
            
                    pages.append({"page":page_num , "words": file})
                else:
                    pages.append({"page": page_num, "words": []})  # empty page
        return pages
    except Exception as e:
        log_exception(e, "extract_text_with_coordinates")
        return []

# ------------ 3. Extract ICD + next word bbox --------------

def extract_icd(pdf_path):
    try:
        with pdfplumber.open(pdf_path) as pdf:
            pages=[]
            icd_results = []
            for page_num, page in enumerate( pdf.pages,start=1):
                words = page.extract_words()
                for i, w in enumerate(words):
                    if w['text'].upper().startswith("ICD-") and "CM:" in w['text'].upper():  # detect ICD
                        if i + 1 < len(words):  # next word exists
                            next_word = words[i + 1]
                            icd_results.append({
                                "page":page_num,
                                "text": next_word.get('text'),
                                "coordinates": {
                                    "x0": next_word.get('x0'),
                                    "y0": next_word.get('y0'),
                                    "x1": next_word.get('x1'),
                                    "y1": next_word.get('y1')
                                }})
                        else:
                            continue
                    else:
                        continue
                if icd_results:
                    pages.append({"ICD CODE": icd_results})
                    icd_results=[]
                else:
                    pages.append({"page":page_num,"ICD CODE": []})
                        
                            
        return pages
    except Exception as e:
        log_exception(e, "extract_icd")
        return []


# --------- Save JSON helper ----------------

def save_as_json(data, output_path):
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        log_exception(e, "save_as_json")

