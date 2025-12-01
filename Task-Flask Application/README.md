
Create a flask application to extract the text and coordinates from input pdf file using pdfplumber and fitz.

3 Methods:
1. Extract text and save as paragraph content
2. Ectract text with coordinates on the words
3. Extract text and filter the ICD codes from the input file with coordinates
4. Highlight the ICD codes using fitz module and save as pdf format

app.py file contain code for main functions and initialization for the function

extract_para.py file contain the functions for the extraction using pdfplumber. filter the ICD codes and save as json file function

Highlight ICD on PDF.ipynb file highlight the ICD code with help of regular expression module and download as pdf highlighted file

output folder contains output samples
