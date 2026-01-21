from typing import (
    List
)

EXCEL_FILETYPE = [".xlsx"]

def is_valid_file_type(filename:str, valid_file_types:List[str])-> bool :
    """Check if file are valid file type using the provided valid_filetypes list"""
    return any(filename.endswith(ext) for ext in valid_file_types)

def is_excel_file(filename:str)->bool:
    valid_file_types = EXCEL_FILETYPE
    return is_valid_file_type(filename, valid_file_types)