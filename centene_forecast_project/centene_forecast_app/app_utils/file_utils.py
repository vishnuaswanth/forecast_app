import json
import os
from django.http import FileResponse,Http404
from typing import(
    List,
)
from .temp_view_data import get_formatted_date
from django.contrib.auth.models import User
from django.conf import settings

def read_json_from_json_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print("Error reading JSON file:", e)
    return data

def read_json(file_name,new_entry=None):
                                                        
    file_path = os.path.join(settings.BASE_DIR, file_name)     # Construct the full path to the JSON file
    data=[]
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print("Error reading JSON file:", e)
    
    if new_entry is not None:
        data.append(new_entry)
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print("Error writing to JSON file:", e)
    return data


def read_json_file(selected_month=None, selected_year=None):
    file_name = "Dec_2024.json" 

    data = read_json(file_name)

    month_1_data = [item for item in data if item["Month"]==get_formatted_date(selected_month,selected_year)]

    return month_1_data

def to_int(val):
    try:
        return int(val)
    except (ValueError, TypeError):
        return None
    

def excel_file_download():
    file_name = "NTT_Amisys.xlsx"
    file_path = os.path.join(settings.BASE_DIR, file_name)
    if os.path.exists(file_path):
        return FileResponse(open(file_path, 'rb'), as_attachment=True, filename="new_file.xlsx")
    else:
        raise Http404("file not found")


