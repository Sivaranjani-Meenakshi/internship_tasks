from fastapi import FastAPI, File, UploadFile, logger, BackgroundTasks
import os,pdfplumber,shutil,json,logging
import config_load
import logging
from pathlib import Path
import shutil,json

config = config_load
app=FastAPI()

upload_dir=Path("input")
log_folder="logs"
output_dir=Path("output")
os.makedirs(log_folder,exist_ok=True)
upload_dir.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    filename="logs/app.log",
    level=logging.ERROR,
    format="%(asctime)s | %(levelname)s | %(funcName)s| Line %(lineno)d | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger=logging.getLogger(__name__)

def data_validation(file: UploadFile =File()):
    try:
        ext = os.path.splitext(file.filename)[1].lower()
        if ext != ".pdf":
            return {"message":"insert valid pdf file"}
        else:
            file_path = upload_dir/ file.filename
            with file_path.open("wb") as f:
                shutil.copyfileobj(file.file,f)  
            return {"message":"validated successfully"}
    except Exception as e:
        logger.error(f"Error occurred: {e}", exc_info=True)
        return {"error": "An data validation error occurred"}

def extract_coordinates(filesd:str,file : UploadFile=File()):
    try:
        results = []
        icd=[]
        with pdfplumber.open(file.file) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                words = page.extract_words()
                for i,w in enumerate(words):
                    if w['text'].upper().startswith("ICD-") and "CM:" in w['text'].upper():
                        if i+1<len(words):
                            next_word=words[i+1]
                            results.append({
                                "text": next_word.get("text"),
                                "x0": next_word.get("x0"),
                                "top": next_word.get("top"),
                                "x1": next_word.get("x1"),
                                "bottom": next_word.get("bottom")
                            })
                            if next_word['text'].endswith(",") and i+2 <len(words):
                                nexn=words[i+2]
                                results.append({
                                    "text": nexn.get("text"),
                                    "x0": nexn.get("x0"),
                                    "top": nexn.get("top"),
                                    "x1": nexn.get("x1"),
                                    "bottom": nexn.get("bottom")
                                })
                            else:
                                continue
                        else:
                            continue
                    else:
                        continue
                text=page.extract_text(regex=True)
                if text and text.strip():
                    paragraphs=text.replace("\n"," ")
                else:
                    paragraphs = [""]
                if results and paragraphs:
                    icd.append({"page":page_num,"ICD Code": results, "para":paragraphs})
                    results=[]
                else:
                    icd.append({"page":page_num,"ICD Code": [],"para":paragraphs})
        with open(filesd, "w", encoding="utf-8") as f:
            json.dump(icd, f, ensure_ascii=False, indent=2)

        return {"message":"File extracted and saved successfully"}

    except Exception as e:
        logging.error(f"Error processing PDF: {e}",exc_info=True)
        return {"error": "An extract coordinates error occurred"}

@app.post("/upload-pdf/")
async def upload_pdf(bgtask : BackgroundTasks,file: UploadFile =File(...)):
    try:
        data = data_validation(file)
        if data.get("message") != "validated successfully":
            return data
        output_dir.mkdir(parents=True, exist_ok=True)
        name=os.path.splitext(file.filename)[0]
        filesd=os.path.join(output_dir,f"bg_{name}.json")

        bgtask.add_task(extract_coordinates,filesd,file)
        return {"validation status": data,
                "Extraction status":"Extracted and saved"}
    
    except Exception as e:
        logger.error(f"Error occurred: {e}", exc_info=True)
        return {"error": "An upload pdf function error occurred"}
