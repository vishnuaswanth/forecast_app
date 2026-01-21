import json
import os
import pandas as pd
from django.conf import settings
from django.urls import reverse
from urllib.parse import urlencode


# Month mapper dictionary
month_mapper = {
    1: 'January', 2: 'February', 3: 'March', 4: 'April',
    5: 'May', 6: 'June', 7: 'July', 8: 'August',
    9: 'September', 10: 'October', 11: 'November', 12: 'December'
}

# Function to get formatted month and year
def get_formatted_date(month:int, year:int) -> str:
    month_name = month_mapper.get(month, None)
    if not month_name:
        return ""
    return f"{month_name}, {year}"

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



# def get_forecast_data(month, boc, insurance_type, locality, process):
#     forecast_json_path = os.path.join(settings.BASE_DIR, "forecast_data.json") 
#     json_data = read_json_from_json_file(file_path=forecast_json_path)
#     print(json_data[month])
#     data = json_data[month][boc][insurance_type][locality][process]
#     return data

def json_actulas(month, boc, insurance_type, locality, process):
    actulas_json_path = os.path.join(settings.BASE_DIR, "actuals.json") 
    json_data = read_json_from_json_file(file_path=actulas_json_path)
    print(json_data[month])
    data = json_data[month][boc][insurance_type][locality][process]
    # column_names = []
    # editable_indices = {}
    # if len(data)>0:
    #     for fields in data[0]:
    #         column_names.append(fields)
    # editable_indices = {
    #                 'CPH': column_names.index('CPH'),
    #                 'CDP': column_names.index('CDP'),
    #                 'Ramp': column_names.index('Ramp')
    #             }
    return data

def read_output_json():
    forecast_json_path = os.path.join(settings.BASE_DIR, "structured_output.json") 
    json_data = read_json_from_json_file(file_path=forecast_json_path)
    return json_data

def read_forecast_data(main_lob,worktype):
    data = read_output_json()
    filtered = {}
    for month, recs in data.get('data', {}).items():
        # apply only the two filters
        out = []
        for rec in recs:
            if main_lob and rec.get('main lob') != main_lob:
                continue
            if worktype and rec.get('worktype') != worktype:
                continue
            out.append(rec)
        filtered[month] = out
    return filtered

def get_tabs_data(output_data, main_lob:str="Main LOB", worktype:str =""):
    tabs_data = []
    month_mapping = output_data.get("tab", {})
    schema_data = output_data.get("schema", {})
    totals_data = output_data.get("totals", {})
    previous_columns = []

    for key in sorted(month_mapping.keys()):  # Month1, Month2, ...
        month = month_mapping[key]
        tab = {
            "key": month,
            "label": month,
            "data_src": "data",
            "table_url": f"{reverse('forecast_app:forecast_table_data')}?{urlencode({'month': month})}",
        }

        month_data = schema_data.get(month, [])
        month_totals_data = totals_data.get(month, None)
        cols = []

        if month_data:
            first_row = month_data[0]
            for col_name in first_row:
                col = {
                    "data": col_name,
                    "title": col_name.upper(),
                }
                if month_totals_data:
                    total_value = month_totals_data.get(col_name, 'ALL')
                    col["footer"] = total_value
                cols.append(col)
            if month_totals_data:
                cols[0]["footer"]=f"Total({main_lob}-{worktype}-{month})"
            previous_columns = cols  # Save for next iteration
        else:
            previous_columns.pop("footer")
            cols = previous_columns  # Reuse last non-empty columns

        tab["columns"] = cols
        # tab["totals"]= totals_data.get(month, [0]*4)  # Use actual totals if available
        tab["totals"]= [10,20, 30, 40]  # Example totals; replace with actual logic if needed
        tabs_data.append(tab)

    return tabs_data

def get_tabs_data_legacy():
    output_data = read_output_json()
    tabs_data = []
    for month in output_data["months"]:
        tab = {}
        tab["key"]= month
        tab["label"] = month
        tab["data_src"] = f"data"
        tab["table_url"]= reverse("forecast_app:forecast_table_data")
        data = output_data['data'][month]
        cols =[]
        for col_name in data[0]:
            col = {}
            col["data"] = col_name
            col["title"] = col_name.upper()

            # if col_name.lower() in ['client forecast', 'fte required', 'fte avail', 'capacity']:
            #     col["editable"] = 'true'
            # col["className"] = "noVis"
            
            cols.append(col)
        tab["columns"]=cols
        print(cols)
        tabs_data.append(tab)
    return tabs_data

def get_roster_colmns(roster_type, cols):
    objects={}  
    # client = APIClient(base_url="http://127.0.0.1:8080")
    # data = client.get_roster_page()
    
    objects["table_id"] = "roster"
    objects["table_url"] = reverse("forecast_app:roster_table_data", args=[roster_type])
    objects["table_props"] = {'destroy':True,'ordering':True,'deferRender':True,'scrollX':True,'processing': True,'serverSide': False,}
    objects["columns"] = cols
    return objects

def get_actuals_colmns(month, boc, insurance_type, locality, process):
    cols=[]
    objects={}
    file_name ="actuals.json"
    data = json_actulas(month, boc.lower(), insurance_type.lower(), locality.lower(), process[:3])

    objects["table_id"] = "actuals"
    objects["table_url"] = reverse("forecast_app:actuals_table_data")
    objects["table_props"] = {'destroy':True, 'searching':False,'lengthChange':False, 'processing': True,'serverSide': False,}
    objects["summations"]=['4','5']
    for col_name in data[0]:
        col={}
        col["data"] = col_name
        if col_name.lower() in ['cph','cdp','ramp']:
            col["editable"] = 'true'
        col["title"] = col_name.upper()
       
        cols.append(col)
    objects["columns"] = cols
    return objects

def filter_data(data):
    Updated_on = "CreatedDateTime"
    file_type = "FileType"

    if not data or not isinstance(data, list):
        return []

    df = pd.DataFrame(data)

    # Ensure required columns exist
    if Updated_on not in df.columns or file_type not in df.columns:
        return []

    # Convert to datetime, coerce errors to NaT
    df[Updated_on] = pd.to_datetime(df[Updated_on], errors='coerce')

    # Drop rows with invalid or missing dates or file_type
    df = df.dropna(subset=[Updated_on, file_type])

    if df.empty:
        return []

    # Sort by file_type and updated_at, descending order of updated_at
    df_sorted = df.sort_values(by=[file_type, Updated_on], ascending=[True, False])

    # Keep the latest file per file_type
    df_unique = df_sorted.drop_duplicates(subset=file_type, keep='first')

    # Sort the result by updated_at descending
    df_result = df_unique.sort_values(by=Updated_on, ascending=False)

    # Format date as string
    df_result[Updated_on] = df_result[Updated_on].dt.strftime('%m/%d/%Y')

    return df_result.to_dict(orient='records')