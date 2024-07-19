import os
import sys
import subprocess
import importlib

used_modules = ["win32com.client", "json", "copy", "re", "getopt"]

def install(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

def setup_modules(used_modules):
    missing_modules = []

    for mod in used_modules:
        try:
            importlib.import_module(mod)
        except ModuleNotFoundError:
            missing_modules.append(mod)
    for mod in missing_modules:
        if mod == "win32com.client":
            install("pywin32")
        else:
            install(mod)
    #print(f"Please re-run the program, some packages were installed")
    #sys.exit(1)
    if len(missing_modules) != 0:
        os.execv(sys.executable, ['python'] + sys.argv)
    
setup_modules(used_modules)

import win32com.client
import os
import json
#import xlwt
##import openpyxl # no excel here
import copy
##from openpyxl.styles import PatternFill # no excel here
##from openpyxl.utils import get_column_letter # no excel here
import re

import getopt

process_map_dict = {
"(A)": "pension, provident fund or social security",
"(B)": "equity share and stock options gains",
}

def free_text_filter(free_text):
    if free_text == "" or free_text == " " or free_text == "-":
        return False
    if re.search(r"^[Nn][.\/\\]?[Aa]", free_text):
        return False
    if re.search(r"^[Nn][Ii][Ll]$", free_text):
        return False
    return True

def process_qns(qns, ans, processed_dict):
    if qns == "(A)" or qns == "(B)":
        if re.search("Yes", ans):
            processed_dict["Structured Data List"].append(process_map_dict[qns])
        return
    if qns == "(C)":
        processed_dict["Structured Data List"] += [option for option in (re.split(r", [a-z]\) ", ans[3:])) if option != "None of the above."]
        return
    if qns == "(D)" or qns == "(E)":
        if free_text_filter(ans):
            processed_dict["Free Text"].append(ans)
        return
    if qns == "(F)":
        if free_text_filter(ans):
            processed_dict["Free Text, not in payroll"].append(ans)
        return

def get_msg_files(some_list_of_files_name):
    return [file_name for file_name in some_list_of_files_name if file_name[-4:]==".msg"]
def get_parsed_json_raw_read(msg_file_abs_path):
    with open(msg_file_abs_path, "r", encoding="utf-8", errors="ignore") as msg_file:
        entire_msg_raw = msg_file.read()
    start_json = '\x00-\x00-\x00 \x00S\x00t\x00a\x00r\x00t\x00 \x00o\x00f\x00 \x00J\x00S\x00O\x00N\x00 \x00-\x00-\x00\n'
    end_json = '\x00-\x00-\x00 \x00E\x00n\x00d\x00 \x00o\x00f\x00 \x00J\x00S\x00O\x00N\x00 \x00-\x00-\x00\n'
    start_json_index = entire_msg_raw.find(start_json) + len(start_json)
    end_json_index = entire_msg_raw.find(end_json)
    if start_json_index == 39 and end_json_index == -1:
        del outlook, msg
        return None
    JSON_portion_raw = entire_msg_raw[start_json_index:end_json_index]
    JSON_portion = re.sub("\x00", "", JSON_portion_raw)
    ## For old messages(.msg) qns formats, naming etc, remove for future so no mismatch parts, accidentally wrong for future ones
    JSON_portion = re.sub(r'\x1a"', "", JSON_portion)
    parsed_json = json.loads(JSON_portion, strict=False)
    return parsed_json
def get_parsed_json_pywin32_module(msg_file_abs_path):
    outlook = win32com.client.Dispatch("Outlook.Application").GetNamespace("MAPI")
    msg = outlook.OpenSharedItem(msg_file_abs_path)

    print(msg_file_abs_path)
    body_portion = msg.Body
    json_start_index = body_portion.find("-- Start of JSON --") + len("-- Start of JSON --")
    json_end_index = body_portion.find("-- End of JSON --")
    if json_start_index == 18 and json_end_index == -1:
        del outlook, msg
        return None
    JSON_portion = body_portion[json_start_index:json_end_index]
    #print(JSON_portion)
    parsed_json = json.loads(JSON_portion)
    del outlook, msg
    return parsed_json
def extract_data_from_msg_file(msg_file_abs_path):
    
    ## Using pywin32, win32com.client module essentially
    parsed_json = get_parsed_json_pywin32_module(msg_file_abs_path)
    
    ## Without the need of pywin32, win32com.client module, using just read file as raw data with like diff formatting and etc
    #parsed_json = get_parsed_json_raw_read(msg_file_abs_path)
    
    if parsed_json == None:
        return None
    #print(type(parsed_json))
    
    extracted_data = {}
    for qns_ans_dict in parsed_json:
        if re.search(r"(\([A-Z]\)$)", qns_ans_dict["question"][-3:]):
            extracted_data[qns_ans_dict["question"][-3:]] = qns_ans_dict["answer"]
    sorted_extracted_data = dict(sorted(extracted_data.items(), key=lambda item:item[0][1]))

    return sorted_extracted_data
def process_extracted_data(extracted_data):
    processed_dict = {"Structured Data List":[], "Free Text":[], "Free Text, not in payroll":[]}
    for qns, ans in extracted_data.items():
        process_qns(qns, ans, processed_dict)
    return processed_dict
def output_extracted_file(output_dir, output_file_name_with_type, extracted_data):
    with open(os.path.join(output_dir, output_file_name_with_type), "w") as output_file:
        json.dump(extracted_data, output_file)
        ## or
        #output_file.write(str(extracted_data))

def extract_from_folder_with_companies_folders(raw_files_folder = "Raw Data", extracted_raw_files_folder = None):
    #print(os.path.join(os.path.realpath('./'), raw_files_folder))
    #print(os.path.dirname(os.path.join(os.path.realpath('./'), raw_files_folder)))
    #print(os.path.basename(os.path.join(os.path.realpath('./'), raw_files_folder)))
    #print(os.path.join(os.path.dirname(os.path.join(os.path.realpath('./'), raw_files_folder)), ("Extracted " + os.path.basename(os.path.join(os.path.realpath('./'), raw_files_folder)))))
    #print("Extracted " + os.path.basename(os.path.join(os.path.realpath('./'), raw_files_folder)))

    raw_files_folder_dir = os.path.basename(os.path.join(os.path.realpath('./'), raw_files_folder))
    
    if extracted_raw_files_folder == None:
        extracted_raw_files_folder = re.sub("(.*)" + raw_files_folder_dir, r"\1Extracted "+raw_files_folder_dir, raw_files_folder)
        #print(extracted_raw_files_folder)

    form_extracted_data_name = "form_extracted_data.json"
    ## not dictionary since no unique key to give/use
    extracted_data_list = []
    
    cur_dir = os.path.realpath(".")
    
    ##extracted_raw_files_folder = ("Extracted "+ raw_files_folder) ## argument fitted
    
    new_extracted_data_folder = os.path.join(cur_dir, extracted_raw_files_folder)
    if not os.path.exists(new_extracted_data_folder):
        os.makedirs(new_extracted_data_folder)
    
    
    companies_folders = next(os.walk(("./"+raw_files_folder)))[1]
    #list_of_raw_companies_folders_abs_path = [os.path.join(cur_dir, raw_files_folder, companies_folder) for companies_folder in companies_folders]
    for company_folder in companies_folders:
        raw_company_folder_abs_path = os.path.join(cur_dir, raw_files_folder, company_folder)
        extracted_raw_company_folder_abs_path = os.path.join(cur_dir, extracted_raw_files_folder, company_folder)
        
        msg_files_list = get_msg_files(next(os.walk(raw_company_folder_abs_path))[2])
        msg_files_abs_path_list = [os.path.join(raw_company_folder_abs_path, msg_file) for msg_file in msg_files_list]
        
        if not os.path.exists(extracted_raw_company_folder_abs_path):
            os.makedirs(extracted_raw_company_folder_abs_path)
        
        #print(msg_files_abs_path_list)
        count = 0
        form_extracted_data_name = "form_extracted_data.json"
        for msg_file_abs_path in msg_files_abs_path_list:
            
            count += 1
            if count > 1:
                form_extracted_data_name = f"form_extracted_data_{count}.json"
                print("Multiple Copies of Msg?!?!")
            extracted_data = extract_data_from_msg_file(msg_file_abs_path)
            if extracted_data == None:
                continue
            processed_extracted_data = process_extracted_data(extracted_data)
            #print(processed_extracted_data)
            #print()
            ## not dictionary since no unique key to give/use
            extracted_data_list.append(processed_extracted_data)
            output_extracted_file(extracted_raw_company_folder_abs_path, form_extracted_data_name, processed_extracted_data)
    return extracted_data_list

def OverallProgram():
    raw_files_folder = extracted_raw_files_folder = None
    somewhat_original_arg = " ".join(sys.argv[1:])
    new_arg_format = [string_c for string_c in re.split(r" ?(-[re]) ?", re.sub(r'\"', r"\\", somewhat_original_arg)) if string_c]
    
    #opts, argss = getopt.getopt(sys.argv[1:], "r:e:")
    opts, argss = getopt.getopt(new_arg_format, "r:e:")
    
    #print(new_arg_format)
    #print(opts)
    
    for opt, val in opts:
        if opt == "-r":
            raw_files_folder = re.sub(r'"$', "", re.sub(r"^.\\", "", val))
        elif opt == "-e":
            extracted_raw_files_folder = re.sub(r'"$', "", re.sub(r"^.\\", "", val))
    #print(raw_files_folder, extracted_raw_files_folder)
    if raw_files_folder == None:
        raw_files_folder = "Raw Data"
    if not os.path.exists(os.path.join(os.path.realpath("./"), raw_files_folder)):
        print(f"The path '{os.path.join(os.path.realpath('./'), raw_files_folder)}' does not exists?!?!")
        print("Have a raw-companies-files-overall-folder named 'Raw Data'")
        print("OR")
        print("Usage: " + sys.argv[0] + " -r raw-companies-files-overall-folder -e extracted-companies-files-overall-folder")
        sys.exit(1)
    if extracted_raw_files_folder != None:
        return extract_from_folder_with_companies_folders(raw_files_folder=raw_files_folder, extracted_raw_files_folder=extracted_raw_files_folder)
    else:
        return extract_from_folder_with_companies_folders(raw_files_folder=raw_files_folder)
    
OverallProgram()