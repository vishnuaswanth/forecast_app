# Centene_Forcast
Django web application for Centene forcast is a Django-based application designed to process forecast data for cases. The client provides forecast data, and based on these inputs, the application calculates and displays the required number of case handlers (agents) in a web view.

## Table of Contents

- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Project Structure](#project-structure)
- [Dependencies](#dependencies)

## Installation





### Prerequisites

- Python 3.x
- Virtual environment tool (recommended)
- Git (to clone the repository)

### Configuration





### Usage








### Project Structure

├───centene_forecast_app
│   ├───migrations
│   │   └───__pycache__
│   ├───static
│   │   └───centene_forecast_app
│   │       └───js
│   ├───templates
│   │   └───centene_forecast_app
│   └───__pycache__
├───centene_forecast_project
│   └───__pycache__
├───core
│   ├───management
│   │   ├───commands
│   │   │   └───__pycache__
│   │   └───__pycache__
│   ├───migrations
│   │   └───__pycache__
│   └───__pycache__
├───middleware
├───static
│   ├───css
│   ├───img
│   └───js
├───staticfiles
│   ├───admin
│   │   ├───css
│   │   │   └───vendor
│   │   │       └───select2
│   │   ├───img
│   │   │   └───gis
│   │   └───js
│   │       ├───admin
│   │       └───vendor
│   │           ├───jquery
│   │           ├───select2
│   │           │   └───i18n
│   │           └───xregexp
│   ├───centene_forecast_app
│   │   └───js
│   ├───css
│   ├───img
│   └───js
├───templates
└───utils

## Utilities Module (`utils.py`)

The `utils.py` These functions include user permission checks, timezone handling, data formatting, and file operations

- **User Permissions:**  
  Functions such as `is_user_editor_or_admin` and `is_user_viewer_editor_or_admin` verify a Django user's group membership. These checks ensure that only users with the appropriate roles (Editor, Admin, or Viewer) can access or modify specific parts of the application.

- **Timezone Handling:**  
  The `get_timezone_info` function accepts an IANA timezone name and returns detailed timezone information including the formatted UTC offset, whether daylight saving time is active, a static timezone abbreviation, and a full timezone name. This function aids in displaying and managing time data accurately based on user or system settings.

- **Data Formatting and Schema Generation:**  
  The `get_table_schema` function processes a list of data rows (dictionaries) to extract column names and arrange data into a tabular format. Additionally, `get_formatted_date` leverages a month mapping to generate a readable date string (e.g., "January, 2024") from numerical month and year values.

- **JSON File Handling:**  
  The `read_json_file` function reads a JSON file from the project’s base directory and filters its contents based on the selected month and year. This facilitates dynamic data loading, especially for projects that rely on external data inputs.

- **Utility Conversion Function:**  
  The `to_int` function safely converts values to integers, returning `None` if the conversion fails. This helps in avoiding runtime errors when dealing with unpredictable data formats.

## File Upload and Asynchronous Processing

The project supports uploading CSV or Excel files, processing them asynchronously, and providing real-time feedback on the processing progress. This functionality is mainly implemented through two modules: `tasks.py` and `views.py`.






### Task Processing with `tasks.py`

- **Function:** `process_uploaded_file(file_upload_id)`
- **Purpose:**  
  Processes an uploaded file in the background using an asynchronous task. The function reads file data (CSV or Excel) with Pandas, processes it in batches, and updates the processing progress and status.
  
- **Key Steps:**
  - **Retrieve File Data:**  
    Fetches the `UploadedFile` record using the provided ID.
  - **File Reading:**  
    - For CSV files: Reads using `pd.read_csv()`.
    - For Excel files: Reads using `pd.ExcelFile()` and selects the correct sheet based on a naming pattern (e.g., `Dec'2024`).
  - **Data Processing:**  
    Processes the file in chunks (100 rows per batch), simulating a delay between batches.
  - **Progress Tracking:**  
    Updates the `progress` field on the `UploadedFile` model, ensuring the front end can track processing progress.
  - **Error Handling:**  
    If any error occurs during processing, the function sets the file status to `error`.

### File Upload via `views.py`

- **View Function:** `upload_view(request)`
- **Purpose:**  
  Manages the file upload interface, validates the uploaded file, stores it in the database, and schedules its processing.

- **Key Steps:**
  - **File Validation:**  
    Ensures the uploaded file has a valid extension (only CSV and Excel files are accepted).
  - **File Storage:**  
    Reads the file content and creates an `UploadedFile` instance in the database.
  - **Asynchronous Processing:**  
    Utilizes Django‑Q's `async_task` to trigger the `process_uploaded_file` function in the background, allowing the main application to remain responsive.
  - **User Feedback:**  
    Returns a JSON response with the file upload ID so that the front end can poll for progress updates.


### Dependencies


