import io
import pandas as pd
import re
import time
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from core.models import UploadedFile

def process_uploaded_file(file_upload_id):
    try:
        file_upload = UploadedFile.objects.get(id=file_upload_id)
        file_bytes = file_upload.file_data
        file_stream = io.BytesIO(file_bytes)
        filename = file_upload.filename

        # Read file depending on its extension
        if filename.endswith('.csv'):
            df = pd.read_csv(file_stream)
        else:
            xls = pd.ExcelFile(file_stream)
            # Find the sheet matching pattern e.g., Dec'2024
            pattern = re.compile(r"^[A-Za-z]{3}'\d{4}$")
            sheet_name = None
            for name in xls.sheet_names:
                if pattern.match(name):
                    sheet_name = name
                    break
            if not sheet_name:
                file_upload.status = 'error'
                file_upload.save()
                return
            df = pd.read_excel(xls, sheet_name=sheet_name)
        total = len(df)
        print(f'total - {total}')
        if total == 0:
            file_upload.status = 'error'
            file_upload.save()
            return
        for i in range(0, total, 100):
            time.sleep(1)  # Simulate processing delay
            chunk = df.iloc[i:i+100]
            print(f'insterted data from {i} to {i+100}')
            # Bulk insert chunk data into UploadData
            # UploadData.objects.bulk_create([
            #     UploadData(
            #         name=row["Name"],
            #         email=row["Email"],
            #         age=row["Age"]
            #     ) for _, row in chunk.iterrows()
            # ])
            progress = min(int((i + 100) / total * 100), 100)
            file_upload.progress = progress
            file_upload.save()
        
        file_upload.status = 'completed'
        file_upload.save()
    except Exception as e:
       file_upload.status = 'error'
       print(f'error - {e}')
       file_upload.save()
    
    
    
    
    
    
