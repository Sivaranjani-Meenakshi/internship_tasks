Task FaskAPI

Extract test and coordinates from pdf file using pdfplumber and using background tasks for fast process to done tasks on fastAPI and save as json file in the output folder.

config.json consist the directory for folder (input,output,log)

config_load.py creates the folder on the current directory

main.py main python file, using faskapi to get file -> validate the input file and using backgrounf taks to assign tasks to the helper function to extract and save the file as json format.
