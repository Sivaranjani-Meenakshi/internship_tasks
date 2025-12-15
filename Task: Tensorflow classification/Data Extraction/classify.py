from fastapi import FastAPI
import os
import logging
import uvicorn
from pathlib import Path
import json,re
from config_load import load_config

# ------------------ CONFIG SETUP ------------------
app = FastAPI()
config = load_config()

FOLDER_DIR = Path("dataset/page_nudata")
TEXT_DIR=Path("dataset/textdataset")
PAGE_DIR = Path("page")
LOG_DIR = Path("logs")
OUTPUT_DIR =Path("output")

FOLDER_DIR.mkdir(parents=True, exist_ok=True)
TEXT_DIR.mkdir(parents=True, exist_ok=True)
PAGE_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True,exist_ok=True)

# --------------------- LOGGING SETUP ----------------
logging.basicConfig(
    filename=LOG_DIR / "app.log",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(funcName)s | Line %(lineno)d | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def get_filenames_from_folder(folder_path: str):
    if not os.path.exists(folder_path):
        raise FileNotFoundError(f"Folder '{folder_path}' does not exist.")
    if not os.path.isdir(folder_path):
        raise NotADirectoryError(f"'{folder_path}' is not a directory.")

    return [
        f for f in os.listdir(folder_path)
        if os.path.isfile(os.path.join(folder_path, f))
    ]


@app.get("/save-filenames")
def save_filenames():
    try:
        filenames = get_filenames_from_folder(FOLDER_DIR)

        results = []
        for fname in filenames:
            file_no_ext = os.path.splitext(fname)[0].split("_")[0]
            file_path = FOLDER_DIR / fname
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            page_nums = []
            if isinstance(data, list):
                for entry in data:
                    if (isinstance(entry, dict) and entry.get("report type") == "laboratory" and "acc_page_num" in entry):
                        page_nums.append(entry["acc_page_num"])
            elif isinstance(data, dict):
                if (data.get("report type") == "laboratory" and "acc_page_num" in data):
                    page_nums.append(data["acc_page_num"])
            pagenu=sorted(set(page_nums))
            results.append({
                "filename": file_no_ext,
                "page_nums": pagenu})

        # Save to JSON file
        PA = PAGE_DIR / "page.json"
        with open(PA, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=4)

        return {"message": "Filenames and page numbers saved successfully"}

    except Exception as e:
        logger.error(f"Error in save_filenames {e}", exc_info=False)
        return {"error": str(e)}


@app.get("/get-filenames")
def get_filenames():
    try:
        PA = PAGE_DIR / "page.json"
        if not os.path.exists(PA):
            raise FileNotFoundError("JSON file not found.")

        with open(PA, "r", encoding="utf-8") as f:
            page_data = json.load(f)
        
        result=[]
        skipped_count=0
        processed_count=0
        for i in page_data:
            fname=i["filename"]
            page_num=i.get("page_nums",[])
            text_file = TEXT_DIR / f"{fname}.json"

            if not text_file.exists():
                logger.warning(f"Text file {text_file} not found, skipping.")
                skipped_count+=1
                continue
            with open(text_file ,"r",encoding="utf-8") as tf:
                text_data = json.load(tf)

            texts = []
            
            for pn in page_num:
                idx = pn - 1
                if 0 <= idx < len(text_data.get("texts", [])):
                    clean=text_data["texts"][idx]
                    cleaned = re.sub(r'\s+', ' ', clean) 
                    cleaned.strip()
                    label = [1 if "lab results" in cleaned.lower() else 0][0]
                    result.append({
                        "filename": fname,
                        "text": cleaned,
                        "label":label
                    })
            processed_count+=1

        pa=OUTPUT_DIR/"file.json"       
        with open (pa, "w",encoding="utf-8")as f:
            json.dump(result,f,indent=4)

        return {"message": "Filenames and text saved successfully",
                "processed_files": processed_count,
                "skipped_files": skipped_count
                }

    except Exception as e:
        logger.error(f"Error in get_filenames {e}", exc_info=False)
        return {"error": str(e)}


if __name__ == "__main__":
    uvicorn.run("classify:app", host="172.17.200.192", port=9867)
