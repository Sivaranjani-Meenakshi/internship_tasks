import requests
import json,re
import sys, datefinder
from datetime import datetime,timedelta
import fitz,os
from tqdm import tqdm
from flask import Flask,request, render_template
from dateutil.parser import parse as dateutil_parse
######### create folders

def load_config(config_path="config.json"):
    with open(config_path, "r") as f:
        config = json.load(f)
    for key in ["INPUT_FOLDER","OUTPUT_FOLDER", "LOG_FOLDER"]:
        folder = config[key]
        if not os.path.exists(folder):
            os.makedirs(folder)
            print(f"Created folder: {folder}")
        else:
            print(f"Folder already exists: {folder}")

    return config

config=load_config()
UPLOAD_FOLDER = config.get("INPUT_FOLDER", "input")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app=Flask(__name__)


######### log writing function

def log_exception(module, logfile=config["LOG_FILE"]):
    exc_type, exc_obj, tb = sys.exc_info()
    log_date = datetime.now()
    lineno = tb.tb_lineno
    ob = '\nTime - {} -->> ERROR IN {} -->> LINE.NO-{} : {}'.format(log_date, module, lineno, exc_obj)

    with open(logfile, 'a', encoding='utf-8') as fp:
        fp.writelines(ob)

def pdf_method(task, text):
    try:
        url = "http://172.16.36.10:9002/"

        payload = json.dumps({
            "prompt": task,
            "text": text
        })
        headers = {
            'Content-Type': 'application/json'
        }
        print("started")
        response = requests.post(url, headers=headers, data=payload)
        #print("response ###",response.json())
        vital_data = json.loads(response.json())
        print("vital_data ####",vital_data)
        
    except Exception as e:
        log_exception("pdf_method")
    return vital_data
 
######## date formating

def parse_date(date_str):
    for fmt in ("%m-%d-%Y", "%m/%d/%y","%m/%d/%Y","%d %b %Y", "%d %B %Y","%Y %m %d"):
        try:
            date_obj = datetime.strptime(date_str, fmt)
            return date_obj.strftime("%m-%d-%Y")
        except ValueError:
            continue
    raise ValueError(f"Invalid date format: {date_str}")

def Accurate_date(date):
    date=parse_date(date)
    DEFAULT_DATE = "01-01-1900"
    try:
        date_obj = dateutil_parse(date,dayfirst=True,fuzzy=True)
        ten_years_ago = datetime.today() - timedelta(days=365 * 15)
        if date_obj < ten_years_ago:
            return DEFAULT_DATE
        return date_obj.strftime("%m-%d-%Y")
    except Exception as e:
        date_obj ='01-01-1900'
    return date_obj
##################################################################

def extraxt_text(pdffile):
    all_texts = []
    ##Get all text in a list
    doc = fitz.open(pdffile)
    page_count = doc.page_count
    for i in range(page_count):
        text = doc[i].get_text()
        all_texts.append(text)
    doc.close()

    return all_texts


###################################################################


vital_query = """
                You are an AI assistant specializing in Vital signs analyzing. Your task is to extract relevant information from patient Vital signs notes based on the provided context. Follow these instructions strictly:
                Use only the information provided in the context. Do not use prior knowledge or external information.

                Extract the following details from the context and output the results as JSON:
                1. Vital Name
                2. Vital value 
                3. Reference range 
                4. Unit of measurement(place units here after removing from "value")
                5. Date  
                6. Classify the report type as one of the following:  
                    - Laboratory  
                    - Radiology  
                    - Cardiology  
                    - Vital signs  
                    - Social history  
                    - Encounters

                **Additional Rules:** 
                1. Vital Name:
                    - Extract the vital signs component name.
                    - Always use the full form for vital names, such as 'weight' instead of 'wt or 'blood pressure' instead of 'BP' or 'o2sat','spo2' instead of Oxygen Saturation.
                    - Don't capture lab component name or others.
                2. Vital value:
                    - Extract the exact component value.
                    - Only capture unique values and exclude reference ranges and unit of measurements. 
                    - If height or weight is given and an imperial value exists, return it; otherwise, keep the values unchanged.
                    - If temperature in provided, return the Fahrenheit value.
                3. Reference range:
                    - Extract the component reference range, if available on context.
                    - Capture proper reference range , don't mapped any refernced context.
                4. Unit of measurement:
                    - Mandatorily extract the unit of measurement whenever a vital value is present in the context.
                5. Date:
                    - Extract the component date of service (mm-dd-yyyy format). 
                    - If one or more date in context, take recent date as Date. 
                    - DO not extract DOB, which is more older date.
                6. report type:
                    - what are the category of the component.
                
                **Output Format:**  
                Ensure the output is enclosed within unique identifiers and is an exact JSON format as shown below: 
                Return ONLY valid JSON
                [{
                    "Vital_name":"",
                    "Vital_value":"",
                    "Reference_range":"",
                    "Unit_of_measurement":"",
                    "Date":"",
                    "report_type":""
                }]
                If any field is not present, mark it as "".

            """


def Vital_classification(all_texts):
    vital_clasify_prompt = """You are an AI assistant specializing in text classification. Your task is to determine if the given content contains vital signs data.  

                            **Instructions:**  
                            - Read the entire content carefully.  
                            - If the content includes vital signs (e.g., heart rate, blood pressure, temperature, respiratory rate, oxygen saturation, weight, height,bmi, etc.),only with values(e.g., 123/45, 45, 45%, 45.6 kg, 10/90/80 0987 ). classify it as `"vitals"`.  
                            - If no vital signs data are present, classify it as `"not_vitals"`.  

                            **Output Format (JSON):**  
                            {
                            "type": "vitals"  // or "not_vitals"
                            }

                        """
    vital_pages = []
    for pagenum,page_text in enumerate(all_texts):
        try:
            if page_text.strip():
                llm_output = pdf_method(text=page_text, task=vital_clasify_prompt)
                #print(llm_output)
                if llm_output:
                    #print("llm",llm_output)
                    if llm_output["type"] == "vitals":
                        vital_pages.append(pagenum+1)
        except Exception as e:
            log_exception("VItal_classification")
    #print("Classified vital Pages : ",vital_pages)

    return vital_pages


def meter_2_feet(unit):
    unit = re.sub("[^0-9.]","",unit)
    try:s=float(unit) * 3.28084
    except:return 0,0
    feet = "{:.1f}".format(s)
    ft,inch = feet.split('.')[0],feet.split('.')[1]
    return ft,inch


def merge_syst_dyst(bp_syst_dyst):
    bp_value = {}
    bp_value["Vital_name"] = "Blood Pressure"
    bp_value["Vital_value"] = f"{bp_syst_dyst[0]['Vital_value']}/{bp_syst_dyst[1]['Vital_value']}"
    bp_value["Date"] = Accurate_date(bp_syst_dyst[0]['Date'])
    bp_value["report_type"] = bp_syst_dyst[0]['report_type']
    bp_value["Unit_of_measurement"] = bp_syst_dyst[0]['Unit_of_measurement']
    bp_value["page_num"] = bp_syst_dyst[0]['page_num']
    bp_value["Height_in_inch"] = bp_syst_dyst[0]['Height_in_inch']
    bp_value["Height_in_feet"] = bp_syst_dyst[0]['Height_in_feet']
    bp_value["Reference_range"] = bp_syst_dyst[0]['Reference_range']

    return bp_value

@app.route('/')
def index():
    return render_template('input.html')

@app.route('/submit', methods=['POST'])
def Find_Vital_Signs():
    file = request.files.get('fileInput') 
    if file: 
        if file.filename.endswith("pdf"):
            file_path = os.path.join(UPLOAD_FOLDER, file.filename)
            file.save(file_path)
            all_texts=extraxt_text(file_path)
            print(all_texts,"all text type: ",type(all_texts))
        elif file.filename.lower().endswith("json"):
            #print("hi.p.")
            try:
                all_texts=[]
                file_path = os.path.join(UPLOAD_FOLDER, file.filename) 
                file.save(file_path) # Now open the saved file and parse JSON 
                with open(file_path, 'r') as f: 
                    data = json.load(f) 
                    texts = data.get("texts", [])
                    for text in texts:
                        alltext = " ".join(text.strip().split())
                        all_texts.append(alltext)
                    print(all_texts,"\n texts type:" ,type(all_texts))
                if not data: 
                    return "Uploaded JSON file is empty." 
            except:
                log_exception("loading json file error")
            
        else:
            return "valid pdf or json file"        
    else: 
        return "Please upload a file OR enter some text."

    vitals_data = []
    def_date = None
    vital_json_output = None
    vital_classified_pages = Vital_classification(all_texts)

    print("Start Vital_LLM Process....")
    print(vital_classified_pages)
    if vital_classified_pages:
        for vital_page_num in tqdm(vital_classified_pages):
            try:
                bp_syst_dyst = [] ## merge Systalic and Dystalic when the data in provided.

                text = all_texts[vital_page_num-1]
                #print(" Start llm process",text)
                vital_llm_response = pdf_method(text=text,task=vital_query)  
                print("vital_llm_response: ",vital_llm_response)
                vital_json_output=vital_llm_response
                if vital_llm_response:
                    for vital_data in vital_llm_response:
                        #try:vital_json_output = json.loads(vital_data)
                        #except:continue
                        vital_json_output=vital_data
                        vital_json_output["Vital_name"] = vital_json_output["Vital_name"].lower().replace("(bmi)","").strip()
                        vital_json_output["page_num"] = vital_page_num
                        vital_json_output["Height_in_feet"] = ""
                        vital_json_output["Height_in_inch"] = ""
                        vital_json_output["Vital_value"] = str(vital_json_output["Vital_value"])
                        #print(vital_json_output)

                ##      remove string in values
                        if vital_json_output["Unit_of_measurement"].lower() in vital_json_output["Vital_value"].lower():
                            vital_json_output["Vital_value"] = vital_json_output["Vital_value"].replace(vital_json_output["Unit_of_measurement"], "")

                        vital_json_output["Vital_name"] = re.sub(r"\(.*?\)","", vital_json_output["Vital_name"]).strip() ##  Replace comments values
            ##          Inititate Height and weight values            
                        if (vital_json_output["Vital_name"].lower() == "height/length" or vital_json_output["Vital_name"].lower() == "height" or vital_json_output["Vital_name"].lower() ==  "body height" or vital_json_output["Vital_name"].lower() == "ht" or vital_json_output["Vital_name"].lower() == "patient-reported height") and vital_json_output["Vital_value"]:
                
                ##    Replace the height Unique name     
                            vital_json_output["Vital_name"] = "Height"

                            vital_json_output["Vital_value"] = vital_json_output["Vital_value"].replace("ft","'").replace("in","").replace("/","'").replace("\\","").replace('"',"").strip()
                            vital_json_output["Vital_value"] = re.sub(r"\(.*?\)|[a-zA-Z]","", vital_json_output["Vital_value"]).strip()  ##  repalce any other special char in data

                            if vital_json_output["Unit_of_measurement"].lower()=="kg" or "lb" in vital_json_output["Vital_value"].lower():
                                continue
                ##          Split feet format
                            ft,inch = "0", "0"
                            ft_inch_check = vital_json_output["Vital_value"].strip().split("'")

                            if len(ft_inch_check)>1:
                                ft,inch = ft_inch_check[0], ft_inch_check[1].replace(",","").strip() if ft_inch_check[1].strip() else "0"
                                vital_json_output["Vital_value"] = vital_json_output["Vital_value"].split(" ")[0]
                                ## vital json output
                                vital_json_output["Unit_of_measurement"] = "feet"

                ##          Split inches format
                            elif "in" in vital_json_output["Unit_of_measurement"].lower():
                                vital_json_output["Unit_of_measurement"] = "inches"

                ##          Split cm format
                            elif "cm" in vital_json_output["Unit_of_measurement"].lower():
                                vital_json_output["Unit_of_measurement"] = "cm"
                
                ##          Convert meter to feet
                            elif "m" == vital_json_output["Unit_of_measurement"].lower():
                                ft,inch = meter_2_feet(vital_json_output["Vital_value"])
                                if ft!=0:
                                    vital_json_output["Unit_of_measurement"] = "feet"

                ##          Split specific feet format
                            elif "ft" in vital_json_output["Unit_of_measurement"].lower():
                                vital_json_output["Unit_of_measurement"] = "feet"
                                ft,inch = vital_json_output["Vital_value"].split(" ")[0].strip(),"0"

                            vital_json_output["Height_in_feet"] = ft.strip()
                            vital_json_output["Height_in_inch"] = inch.strip().replace('"','')

                        elif vital_json_output["Vital_name"].lower() == "weight" or vital_json_output["Vital_name"].lower() == "wt" or vital_json_output["Vital_name"].lower() == "dosing weight" or vital_json_output["Vital_name"].lower() == "patient-reported weight":
                    ##    Replace the height Unique name     
                            vital_json_output["Vital_name"] = "Weight"

                            vital_json_output["Vital_value"] = re.sub(r"\(.*?\)","", vital_json_output["Vital_value"]).strip()
                            vital_json_output["Unit_of_measurement"] = re.sub(r"\(.*?\)","", vital_json_output["Unit_of_measurement"]).strip()
                            convert_kg_to_lb = vital_json_output["Vital_value"]
                            
                            vital_json_output["Vital_value"] = convert_kg_to_lb.split()[0] if convert_kg_to_lb else convert_kg_to_lb
                    
                    ##     Replace any captured string
                            vital_json_output["Vital_value"] = re.sub("[^.0-9]","", vital_json_output["Vital_value"])
                            
                            lbs_match = [a for a in ["lb","pound", "ib"] if a in vital_json_output["Unit_of_measurement"].lower()]
                            lbs_match_1 = [a for a in ["lb", "ib"] if a in convert_kg_to_lb.lower()]
                            if lbs_match or lbs_match_1:
                                vital_json_output["Unit_of_measurement"] = "lbs"
                            elif "kg" in convert_kg_to_lb.lower():
                                vital_json_output["Unit_of_measurement"] = "kg"
                            
                        else:
                            #vital_json_output["Vital_value"] = vital_json_output["Vital_value"].split()[0] if vital_json_output["Vital_value"] else vital_json_output["Vital_value"]
                            vital_json_output["Vital_value"] = vital_json_output["Vital_value"].split()[0] if "/" not in vital_json_output["Vital_value"] else vital_json_output["Vital_value"]
                            if vital_json_output["Vital_name"].lower()=="blood pressure" and "." in vital_json_output["Vital_value"]:
                                split_val = vital_json_output["Vital_value"].split("/")
                                if len(split_val)>1:
                                    try:vital_json_output["Vital_value"] = f"{round(float(split_val[0]))}/{round(float(split_val[1]))}"
                                    except:pass
                
                    ##     Merge Systolic and diastolic
                            if "systolic" in vital_json_output["Vital_name"].lower():
                                bp_syst_dyst.append(vital_json_output)
                            elif "diastolic" in vital_json_output["Vital_name"].lower():
                                bp_syst_dyst.append(vital_json_output)
                            elif len(bp_syst_dyst)==2:
                                bp_value = merge_syst_dyst(bp_syst_dyst)
                                vitals_data.append(bp_value)
                                bp_syst_dyst = []

                    ##  Replace SpO2 Name
                            if "o2" in vital_json_output["Vital_name"].lower() or "saturation" in vital_json_output["Vital_name"].lower() or "pulse ox" in vital_json_output["Vital_name"].lower():
                                vital_json_output["Vital_name"] = "Oxygen Saturation"

                    ##  Replace BMI  name
                            if "bmi" in vital_json_output["Vital_name"].lower():
                                vital_json_output["Vital_name"] = "Body Mass Index"
                    
                    ##  Replace BP  name
                            if "bp"==vital_json_output["Vital_name"].lower() or "blood pressure" in vital_json_output["Vital_name"].lower():
                                vital_json_output["Vital_name"] = "Blood pressure"
                    
                    #  Replace Pulse  name
                            if "pulse rate" in vital_json_output["Vital_name"].lower() or "patient-reported pulse" in vital_json_output["Vital_name"].lower():
                                vital_json_output["Vital_name"] = "Pulse"


                        vital_json_output["Date"] = Accurate_date(vital_json_output["Date"])
            ##        Mapped recent date
                        if def_date  and vital_json_output["Date"]=="01-01-1900":
                            vital_json_output["Date"] = def_date

                        if vital_json_output["report_type"].lower()== 'vital signs' and vital_json_output["Vital_value"]:
                            vitals_data.append(vital_json_output)    
            
                        if vital_json_output:
                            def_date = vital_json_output["Date"]

                ##  Append systalic and dystalic data    
                    if len(bp_syst_dyst)==2:
                        bp_value = merge_syst_dyst(bp_syst_dyst)
                        vitals_data.append(bp_value)
                        bp_syst_dyst = []
                
            except:
                log_exception("Vitals_extraction on Find_Vital_Signs")
    print("2222",vitals_data)

    #return vitals_data
    return render_template('output.html', result=vitals_data)
    
if __name__ == "__main__":
    app.run(host='172.17.200.192', port=6547)