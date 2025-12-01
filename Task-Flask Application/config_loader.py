import os
import json

def load_config(config_path="config.json"):
    with open(config_path, "r") as f:
        config = json.load(f)

    # Ensure folders exist (only create if missing)
    for key in ["INPUT_FOLDER", "OUTPUT_FOLDER", "LOG_FOLDER"]:
        folder = config[key]
        if not os.path.exists(folder):
            os.makedirs(folder)
            print(f"Created folder: {folder}")
        else:
            print(f"Folder already exists: {folder}")

    return config
