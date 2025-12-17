There are two types of json content in different folder need to extract the relavent datas and combine on single json file for further process.
**
function 1: save-filenames function**

page.json is output from save-filename function it opens the folder_dir and read the filename and acc_page_nums from the files and append to the page.json file.

input file name sample: number_labs.json,

output as filename,page_num in json format.


**function 2: get-filenames function**

file.json contain read the page.json file and try to find the file from text_dir folder extract text which is equal to acc_page_nums and write on file.json file with respective labels (1 when it contain "lab results" on the sentences, otherwise 0)

input get page.json and text_dir

output as filename,text,label in json format.
