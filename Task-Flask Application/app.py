from flask import Flask, request, jsonify
import os,sys
from config_loader import load_config
from werkzeug.utils import secure_filename
from extract_para import *

app = Flask(__name__)

# Load config
config = load_config()

# Folder to save uploaded PDFs
UPLOAD_FOLDER = config.get("INPUT_FOLDER", "input")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Allowed file extensions
ALLOWED_EXTENSIONS = {'pdf'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 20 * 1024 * 1024  # 10 MB

def allowed_file(filename):
    """Check if file has an allowed extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/", methods=["POST"])
def main():
    try:
        # Check if file part is present
        if 'file' not in request.files:
            return jsonify({"error": "No file part in request"}), 400

        file = request.files['file']

        # If no file is selected
        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400

        # Validate file type
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)

            # Choose library from config
            library = config.get("LIBRARY", "pdfplumber")

            
            #------------------ 1. Paragraph extraction------------------
           
            if library == "pdfplumber":
                paragraphs = extract_text_pdfplumber(file_path)
            else:
                paragraphs = extract_text_pdfplumber(file_path)

            output_paragraphs = os.path.join(config["OUTPUT_FOLDER"], f"{filename}_paragraphs.json")
            save_as_json(paragraphs, output_paragraphs)

      
            # ---------- 2. Word + coordinates extraction ---------------
     
            coordinates = extract_text_with_coordinates(file_path)
            output_coordinates = os.path.join(config["OUTPUT_FOLDER"], f"{filename}_coordinates.json")
            save_as_json(coordinates, output_coordinates)

           
            # ---------- 3. ICD detection ---------------------------------
          
            icd_data = extract_icd(file_path)
            output_icd = os.path.join(config["OUTPUT_FOLDER"], f"{filename}_icd.json")
            save_as_json(icd_data, output_icd)
            data=[paragraphs,icd_data]
            output_data=os.path.join(config["OUTPUT_FOLDER"],f"{filename}_para_&_icd.json")
            save_as_json(data,output_data)
            return jsonify({"message": "All extractions complete",
                             "outputs": {
                                "paragraphs": output_paragraphs,
                                 "coordinates": output_coordinates,
                                 "icd": output_icd,
                                 "Extract":output_data}})
        

    except Exception as e:
        log_exception(e, "main")
        return jsonify({"error": str(e)}), 500
    finally:
        file.close()

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=6547)
