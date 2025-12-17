import tensorflow as tf
from pydantic import BaseModel
import numpy as np
from fastapi import FastAPI,UploadFile,File
import logging, uvicorn, os, joblib, pdfplumber,shutil
from pathlib import Path
from tensorflow import keras
from tensorflow import keras
from tensorflow.keras import layers
from tensorflow.keras.callbacks import EarlyStopping
from tensorflow.keras.preprocessing.sequence import pad_sequences

from config_load import load_config
app = FastAPI()
config=load_config()

INPUT_DIR = Path("input")
OUTPUT_DIR =Path("output")
LOG_DIR = Path("logs")

INPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    filename=LOG_DIR / "app.log",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(funcName)s | Line %(lineno)d | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ------------------ DATA VALIDATION ------------------
def data_validation(file: UploadFile):
    try:
        ext = os.path.splitext(file.filename)[1].lower()
        if ext != ".pdf":
            return None, "Insert valid PDF file"

        file_path = INPUT_DIR / file.filename
        with file_path.open("wb") as f:
            shutil.copyfileobj(file.file, f)

        return str(file_path), None
    except Exception as e:
        logger.error(f"Error saving file: {e}", exc_info=True)
        return None, "Internal file save error"

def extract_text(pdf_path: str):
    results = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text() or ""
                results.append({
                    "page": page.page_number,
                    "para": page_text.replace("\n", " ").strip()
                })
        return results
    except Exception as e:
      logger.error(f"Error in extract_text {e}", exc_info=False)

def load_model():
    global model
    model_path = r"C:\Users\sivaranjani.m\Documents\python_stu\tensorprojet\model.h5"

    try:
        model = keras.models.load_model(model_path)
        return model
    except Exception as e:
        logger.error(f"Error in load_model: {e}", exc_info=False)

@app.post("/predict")
async def predict(file: UploadFile = File(...)):
    try:
        pdf_path, error = data_validation(file)
        if error:
            return {"status": "error", "message": error}
        df=extract_text(pdf_path)
        page=[d['page'] for d in df]
        texts = [d['para'] for d in df]
        result=[]
        model=load_model()
        if model is None:
            logger.error("Model is None")
            return {"status": "error", "message": "Model not loaded"}
        # One-hot encode
        for i, text in zip(page, texts):
            text_one_hot = [tf.keras.preprocessing.text.one_hot(text, 50)]
            text_padded = pad_sequences(text_one_hot, maxlen=12, padding='post')

            predict_result = model.predict(text_padded)
            ylabel =int(predict_result > 0.5)
            result.append({
                "page": i,
                "label": ylabel
            })

        return result
    except Exception as e:
        logger.error(f"Error in predict: {e}", exc_info=False)


if __name__ =="__main__":
    uvicorn.run("main:app",host="172.17.200.192",port=9347)