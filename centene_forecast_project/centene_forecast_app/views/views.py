import os
import datetime
import urllib.parse

from django.contrib import messages
from django.http import JsonResponse
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import render, redirect

from core.models import UploadedFile

from utils import *
from centene_forecast_app.repository import *
from centene_forecast_app.app_utils import *
from centene_forecast_app.repository import APIClient
from centene_forecast_app.context import *

# Data view validators
from centene_forecast_app.validators.dataview_validators import (
    validate_year,
    validate_month,
    validate_platform,
    validate_market,
    validate_locality,
    ValidationError
)


# Data view services
from centene_forecast_app.services.dataview_service import (
    get_initial_filter_options,
    get_months_for_year,
    get_platforms_for_selection,
    get_markets_for_platform,
    get_localities_for_selection,
    get_worktypes_for_selection
)

# Data view serializers
from centene_forecast_app.serializers.dataview_serializers import (
    serialize_filter_options_response,
    serialize_cascade_response,
    serialize_error_response
)

# Cache utilities
from centene_forecast_app.app_utils.cache_utils import (
    clear_forecast_cache,
    clear_roster_cache,
    clear_summary_cache,
    clear_cascade_caches,
    clear_all_caches
)

import logging

logger = logging.getLogger('django')

BASE_URL = getattr(settings, 'API_BASE_URL' , "http://127.0.0.1:8080")

def login_view(request):
    """Handles user login"""
    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')

        request.session['portal_id'] =  username

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect("forecast_app:time_zone")
        else:
            messages.error(request, "Invalid username or password")
    return render(request, "login.html")

@login_required
def timezone_selection(request):
    if request.method == 'POST':
        selected_timezone = request.POST.get('timezone')

        request.session['timezone'] = selected_timezone  # Save to session
        return redirect("forecast_app:upload")
    # Get a list of common time zones
    timezones = [
        ("Asia/Kolkata", "Indian Standard time (IST)"),
        ("America/Chicago", "Central Standard Time (CST)"),
        ("America/New_York", "Eastern Standard Time (EST)"),
    ]

    context = {
        'timezones': timezones,
        'title':'TimeZone'
    }

    return render(request,"timezone.html", context)

@login_required
@permission_required(get_permission_name("view"), raise_exception=True)
def home_view(request):

    portal_id =  request.session.get('portal_id')

    column_names, row_data = get_table_schema(read_json_file("december_2024.json"))

    user = User.objects.get(username=portal_id)
    full_name = user.first_name +" "+user.last_name


    context = {
        'title':'Home',
        'user_name' : full_name,
        'headers': column_names,
        'data': row_data[:10],
        
    }
    return render(request,"home.html", context)



@login_required
@permission_required(get_permission_name("add"), raise_exception=True)
def upload_view(request):
    logger.info("Entered upload_view for user: %s", request.user.username)
    column_names = []
    row_data = [] 
    client = get_api_client()
    if request.method == 'POST':
        uploaded_file = request.FILES.get('file')
        file_type =request.POST.get('filetype')
        logger.debug("POST upload_view: file_type=%s, uploaded_file=%s", file_type, uploaded_file)
        if not uploaded_file:
            logger.warning("No file uploaded by user: %s", request.user.username)
            return JsonResponse(
                serialize_error_response('No file uploaded.', 400),
                status=400
            )
        if not uploaded_file.name.endswith(('.csv', '.xlsx')):
            logger.warning("Invalid file type uploaded: %s", uploaded_file.name)
            return JsonResponse(
                serialize_error_response('Invalid file type. Only CSV and Excel files are allowed.', 400),
                status=400
            )
        file_content = uploaded_file.read()
        user_name = f"{request.user.first_name} {request.user.last_name}".strip()

        response = None 
        try:       
            if file_type == 'roster':
                response = client.upload_roster_file(
                    file_content=file_content,
                    filename=uploaded_file.name,
                    user= user_name
                )
            elif file_type == 'forecast':
                response = client.upload_forecast_file(
                    file_content=file_content,
                    filename=uploaded_file.name,
                    user= user_name
                )
            elif file_type == 'prod_team_roster':
                response = client.upload_prod_team_roster_file(
                    file_content=file_content,
                    filename=uploaded_file.name,
                    user= user_name
                )
            elif file_type == 'altered_forecast':
                response = client.upload_altered_forecast_file(
                    file_content=file_content,
                    filename=uploaded_file.name,
                    user= user_name
                )
            else:
                logger.error("Unsupported file type: %s", file_type)
                return JsonResponse(
                    serialize_error_response('Unsupported file type', 400),
                    status=400
                )
        except Exception as e:
            logger.exception("Exception during file upload: %s", str(e))
            return JsonResponse(
                serialize_error_response('Upload failed due to server error', 500),
                status=500
            )
        
        if 'error' in response:
            logger.error("Upload failed with error: %s", response['error'])
            return JsonResponse(
                serialize_error_response(response['error'], 400),
                status=400
            )

        if response is None:
            logger.error("Upload failed, response is None")
            return JsonResponse(
                serialize_error_response('Upload failed', 500),
                status=500
            )
        
        # Clear relevant caches after successful upload
        # Extract month and year from response or filename if available
        # For now, clear all caches for safety
        try:
            if file_type == 'roster':
                logger.info("Clearing roster caches after successful upload")
                # Clear all roster caches (all months/years since we don't have specifics)
                clear_cascade_caches()
                # clear_roster_cache() TODO: try getting month and year from filename
                logger.info("Note: Cleared cascade caches. Roster data cache will expire naturally.")
            elif file_type == 'forecast' or file_type == 'altered_forecast':
                logger.info("Clearing forecast caches after successful upload")
                # Clear all forecast-related caches
                clear_all_caches()

                # NEW: Clear filter options cache for LLM chat validation
                try:
                    from chat_app.utils.filter_cache import get_filter_cache
                    filter_cache = get_filter_cache()
                    filter_cache.clear_all()
                    logger.info("Cleared filter options cache for LLM chat validation")
                except ImportError:
                    logger.debug("Filter cache not available (chat_app not installed)")
                except Exception as filter_cache_error:
                    logger.warning(f"Failed to clear filter cache: {filter_cache_error}")

                logger.info("Note: Cleared cascade caches. Forecast data cache will expire naturally.")
            elif file_type == 'prod_team_roster':
                logger.info("Clearing prod team roster caches after successful upload")
                # clear_roster_cache() TODO: try getting month and year from filename
                clear_cascade_caches()
                logger.info("Note: Cleared cascade caches. Roster data cache will expire naturally.")
        except Exception as cache_error:
            # Don't fail the upload if cache clearing fails
            logger.warning(f"Failed to clear caches after upload: {cache_error}")

        logger.info("File uploaded successfully: %s", uploaded_file.name)
        return JsonResponse({
            'success': True,
            'message': response.get('message', "some error fetching message")
        }, status=200)
    try:
        data = client.get_all_record_history()
        records =[]
        if data:
            records = data.get('records', [])
        logger.debug("Fetched %d records from API", len(records))
        filtered_data = filter_data(records)
        logger.debug("Filtered data to %d records", len(filtered_data))
        column_names, row_data = get_table_schema(filtered_data)
    except Exception as e:
        logger.exception("Error fetching or processing records: %s", str(e))
        column_names, row_data = [], []
    context = {
        'title':'Uploadview',
        'column_names': column_names,
        'row_data':row_data,
    }
    logger.info("Rendering upload_view page for user: %s", request.user.username)
    return render(request,"pages/upload_view.html", context)

@login_required
@permission_required(get_permission_name("view"), raise_exception=True)
def forecast_data_table(request):
    logger.info("Entered forecast_data_table data for user: %s", request.user.username)
    page = request.GET.get("draw")
    tab_month = request.GET.get("month")
    keys = request.session.get('Filters', {})
    selected_month, selected_year = to_int(keys.get('selected_month')), to_int(keys.get('selected_year'))
    main_lob, worktype = keys.get('main_lob'), keys.get('worktype')
    logger.debug("Filters from session: month=%s, year=%s, main_lob=%s, worktype=%s", selected_month, selected_year, main_lob, worktype)
    client = get_api_client()
    data = client.get_all_forecast_records(selected_month, selected_year, tab_month, main_lob, worktype)
    # read_forecast_data(main_lob, worktype)
    response = {
        "draw":1,
        "recordsTotal":len(data),
        "data": data
    }
    logger.debug("Returning response with %d records", len(data))
    logger.info(f"completed forecast data call")
    return JsonResponse(response, safe=False)

@login_required
@permission_required(get_permission_name("view"), raise_exception=True)
def roster_data_table(request, roster_type:str):
    logger.info("Entered roster_data_table view for user: %s", request.user.username)
    page = request.GET.get("draw")
    keys = request.session.get('Filters', {})
    selected_month, selected_year = keys.get('selected_month'), keys.get('selected_year')
    logger.debug("Filters from session: month=%s, year=%s", selected_month, selected_year)
    client = get_api_client()
    try:
        data = client.get_all_roster(roster_type, month=int(selected_month), year=int(selected_year))
        logger.info("Fetched %d roster records for month=%s, year=%s", len(data), selected_month, selected_year)
    except Exception as e:
        logger.exception("Error fetching roster data for month=%s, year=%s: %s", selected_month, selected_year, str(e))
        data = []
    response = {
        "draw": 1,
        "recordsTotal": len(data),
        "data": data
    }
    logger.debug("Returning response with %d records", len(data))
    return JsonResponse(response, safe=False)

@login_required
@permission_required(get_permission_name("view"), raise_exception=True)
def actuals_data_table(request):
    filt_val = ('month','boc','insurance_type','locality','process')

    page = request.GET.get("draw")
    keys = request.session.get('Filters', {})
    month, boc, insurance_type, locality, process = (keys.get(key) for key in filt_val)
    
    data = json_actulas(month, boc.lower(), insurance_type.lower(), locality.lower(), process[:3])
    response = {
        "draw":1,
        "recordsTotal":len(data),
        "data": data
    }
    return JsonResponse(response, safe=False)

@login_required
@permission_required(get_permission_name("view"), raise_exception=True)
def forecast_filter_years_api(request):
    """
    API endpoint for fetching available years for forecast filters.

    URL: /forecast/filter-years/
    Method: GET

    Returns:
        JSON response with years list
    """
    logger.info(f"Forecast filter years API called by user: {request.user.username}")

    try:
        options = get_initial_filter_options()
        response = serialize_filter_options_response(options)
        if response["success"]:
            logger.info("Forecast filter years API success")
            return JsonResponse(response, status=200)
        else:
            return JsonResponse(response, status=400)

    except Exception as e:
        logger.error(f"Error in forecast filter years API: {str(e)}", exc_info=True)
        return JsonResponse(
            serialize_error_response("Failed to fetch filter years", 500),
            status=500
        )

@login_required
@permission_required(get_permission_name("view"), raise_exception=True)
def forecast_months_api(request):
    """
    API endpoint for fetching months for selected year (cascading).

    URL: /forecast/months/
    Method: GET
    Query Params: year (required)

    Returns:
        JSON response with months list
    """
    year = request.GET.get('year', '').strip()

    logger.info(
        f"Forecast months API called - year: {year} "
        f"(user: {request.user.username})"
    ) # TODO change it to debug

    try:
        # Validate year
        year_int = validate_year(year)

        # Get months
        months = get_months_for_year(year_int)
        response = serialize_cascade_response(months, 'months')

        logger.info(f"Forecast months API success - {len(months)} months returned")
        return JsonResponse(response, status=200)

    except ValidationError as e:
        logger.warning(f"Validation error in forecast months API: {str(e)}")
        return JsonResponse(serialize_error_response(str(e), 400), status=400)

    except Exception as e:
        logger.error(f"Error in forecast months API: {str(e)}", exc_info=True)
        return JsonResponse(
            serialize_error_response("Failed to fetch months", 500),
            status=500
        )

@login_required
@permission_required(get_permission_name("view"), raise_exception=True)
def forecast_platforms_api(request):
    """
    API endpoint for fetching platforms for selected year/month (cascading).

    URL: /forecast/platforms/
    Method: GET
    Query Params: year (required), month (required)

    Returns:
        JSON response with platforms list
    """
    year = request.GET.get('year', '').strip()
    month = request.GET.get('month', '').strip()

    logger.info(
        f"Forecast platforms API called - year: {year}, month: {month} "
        f"(user: {request.user.username})"
    ) # TODO change it to debug

    try:
        # Validate parameters
        year_int = validate_year(year)
        month_int = validate_month(month)

        # Get platforms
        platforms = get_platforms_for_selection(year_int, month_int)
        response = serialize_cascade_response(platforms, 'platforms')

        logger.info(f"Forecast platforms API success - {len(platforms)} platforms returned")
        return JsonResponse(response, status=200)

    except ValidationError as e:
        logger.warning(f"Validation error in forecast platforms API: {str(e)}")
        return JsonResponse(serialize_error_response(str(e), 400), status=400)

    except Exception as e:
        logger.error(f"Error in forecast platforms API: {str(e)}", exc_info=True)
        return JsonResponse(
            serialize_error_response("Failed to fetch platforms", 500),
            status=500
        )

@login_required
@permission_required(get_permission_name("view"), raise_exception=True)
def forecast_markets_api(request):
    """
    API endpoint for fetching markets for selected platform (cascading).

    URL: /forecast/markets/
    Method: GET
    Query Params: year, month, platform (all required)

    Returns:
        JSON response with markets list
    """
    year = request.GET.get('year', '').strip()
    month = request.GET.get('month', '').strip()
    platform = request.GET.get('platform', '').strip()

    logger.info(
        f"Forecast markets API called - year: {year}, month: {month}, "
        f"platform: {platform} (user: {request.user.username})"
    ) # TODO change it to debug

    try:
        # Validate parameters
        year_int = validate_year(year)
        month_int = validate_month(month)
        platform_str = validate_platform(platform)

        # Get markets
        markets = get_markets_for_platform(year_int, month_int, platform_str)
        response = serialize_cascade_response(markets, 'markets')

        # TODO change it to debug
        logger.info(f"Forecast markets API success - {len(markets)} markets returned")
        return JsonResponse(response, status=200)

    except ValidationError as e:
        logger.warning(f"Validation error in forecast markets API: {str(e)}")
        return JsonResponse(serialize_error_response(str(e), 400), status=400)

    except Exception as e:
        logger.error(f"Error in forecast markets API: {str(e)}", exc_info=True)
        return JsonResponse(
            serialize_error_response("Failed to fetch markets", 500),
            status=500
        )

@login_required
@permission_required(get_permission_name("view"), raise_exception=True)
def forecast_localities_api(request):
    """
    API endpoint for fetching localities for selected platform/market (cascading).

    URL: /forecast/localities/
    Method: GET
    Query Params: year, month, platform, market (all required)

    Returns:
        JSON response with localities list (includes 'All' since optional)
    """
    year = request.GET.get('year', '').strip()
    month = request.GET.get('month', '').strip()
    platform = request.GET.get('platform', '').strip()
    market = request.GET.get('market', '').strip()

    logger.info(
        f"Forecast localities API called - year: {year}, month: {month}, "
        f"platform: {platform}, market: {market} (user: {request.user.username})"
    ) # TODO change it to debug

    try:
        # Validate parameters
        year_int = validate_year(year)
        month_int = validate_month(month)
        platform_str = validate_platform(platform)
        market_str = validate_market(market)

        # Get localities
        localities = get_localities_for_selection(
            year_int, month_int, platform_str, market_str
        )
        response = serialize_cascade_response(localities, 'localities')

        logger.info(f"Forecast localities API success - {len(localities)} localities returned")
        return JsonResponse(response, status=200)

    except ValidationError as e:
        logger.warning(f"Validation error in forecast localities API: {str(e)}")
        return JsonResponse(serialize_error_response(str(e), 400), status=400)

    except Exception as e:
        logger.error(f"Error in forecast localities API: {str(e)}", exc_info=True)
        return JsonResponse(
            serialize_error_response("Failed to fetch localities", 500),
            status=500
        )

@login_required
@permission_required(get_permission_name("view"), raise_exception=True)
def forecast_worktypes_api(request):
    """
    API endpoint for fetching worktypes for selected filters (cascading).

    URL: /forecast/worktypes/
    Method: GET
    Query Params: year, month, platform, market (required), locality (optional)

    Returns:
        JSON response with worktypes list
    """
    year = request.GET.get('year', '').strip()
    month = request.GET.get('month', '').strip()
    platform = request.GET.get('platform', '').strip()
    market = request.GET.get('market', '').strip()
    locality = request.GET.get('locality', '').strip()

    logger.info(
        f"Forecast worktypes API called - year: {year}, month: {month}, "
        f"platform: {platform}, market: {market}, locality: {locality or 'all'} "
        f"(user: {request.user.username})"
    ) # TODO change it to debug

    try:
        # Validate parameters
        year_int = validate_year(year)
        month_int = validate_month(month)
        platform_str = validate_platform(platform)
        market_str = validate_market(market)
        locality_str = validate_locality(locality)  # Returns None if empty

        # Get worktypes
        worktypes = get_worktypes_for_selection(
            year_int, month_int, platform_str, market_str, locality_str
        )
        response = serialize_cascade_response(worktypes, 'worktypes')

        logger.info(f"Forecast worktypes API success - {len(worktypes)} worktypes returned")
        return JsonResponse(response, status=200)

    except ValidationError as e:
        logger.warning(f"Validation error in forecast worktypes API: {str(e)}")
        return JsonResponse(serialize_error_response(str(e), 400), status=400)

    except Exception as e:
        logger.error(f"Error in forecast worktypes API: {str(e)}", exc_info=True)
        return JsonResponse(
            serialize_error_response("Failed to fetch worktypes", 500),
            status=500
        )

@login_required
@permission_required(get_permission_name("view"), raise_exception=True)
def data_view(request):
    logger.info("Entered data_view for user: %s", request.user.username)
    client = get_api_client()

    error_message = ""
    info_message = ""
    years = client.get_forecast_filter_years()

    # Handle API error response
    if is_api_error(years):
        error_message = years.get('error', 'Failed to fetch filter years')
        logger.error("Failed to fetch filter years: %s", error_message)
        years = {}  # Fallback to empty dict

    logger.debug("years: %s", years)
    options = get_dropdown_options(years)

    dropdown_names = ['data_type', 'platform', 'worktype', 'market', 'locality', 'month', 'year', 'summary_type']
    dropdown_values = {name: request.GET.get(name, '') for name in dropdown_names}
    logger.debug("Dropdown values: %s", dropdown_values)

    data_type = dropdown_values.get('data_type')
    selected_month = to_int(dropdown_values.get('month'))
    selected_year = to_int(dropdown_values.get('year'))

    logger.debug("Selected data_type: %s, month: %s, year: %s", data_type, selected_month, selected_year)

    tabs = []
    objects = {}

    html_summary_table = None
    if request.GET:
        # Validate month and year selections
        if not selected_month or not selected_year:
            error_message = "Please select both month and year."
            logger.warning("Month or year not selected: month=%s, year=%s", selected_month, selected_year)
        else:
            try:
                if data_type == "roster" or data_type == "prod_team_roster":
                    request.session['Filters'] = {
                        'selected_month': selected_month,
                        'selected_year': selected_year,
                    }
                    logger.info("Set session Filters for roster: %s", request.session['Filters'])
                    roster_columns = client.get_roster_model_schema(data_type, selected_month, selected_year)
                    objects = get_roster_colmns(data_type, roster_columns.get('schema', []))
                    logger.debug("Fetched roster columns: %s", objects)
                elif data_type == "forecast":
                    platform = dropdown_values.get('platform', '')
                    market = dropdown_values.get('market', '')
                    locality = dropdown_values.get('locality', '')
                    worktype = dropdown_values.get('worktype', '')

                    # Build main_lob from new parameters (skip locality if empty)
                    lob_parts = [platform, market]
                    if locality and locality.lower() != 'select':
                        lob_parts.append(locality)
                    main_lob:str = ' '.join(lob_parts)
                    main_lob = main_lob.strip()

                    request.session['Filters'] = {
                        'selected_month': selected_month,
                        'selected_year': selected_year,
                        'main_lob': main_lob,
                        'worktype': worktype,
                        'platform': platform,
                        'market': market,
                        'locality': locality,
                    }
                    logger.info("Set session Filters for forecast: %s", request.session['Filters'])
                    schema_response = client.get_forecast_model_schema(selected_month, selected_year, main_lob, worktype)
                    tabs = get_tabs_data(schema_response, main_lob=main_lob, worktype=worktype)
                    logger.debug("Fetched tabs data: %s", tabs)
                elif data_type == "summary":
                    summary_type = dropdown_values.get('summary_type', '')
                    logger.info(f"Handling summary request for month: {selected_month} year: {selected_year} summary_type: {summary_type}")
                    request.session['Filters'] = {
                        'selected_month': selected_month,
                        'selected_year': selected_year,
                        'summary_type': summary_type,
                    }
                    logger.info("Set session Filters for summary: %s", request.session['Filters'])
                    output = client.get_table_summary(
                        summary_type, selected_month, selected_year
                    )
                    # logger.debug("Fetched summary columns: %s", objects)
                    if 'error' in output:
                        error_message = output['error']
                        logger.error("Error fetching summary data: %s", error_message)
                    else:
                        html_summary_table = output
            except Exception as e:
                logger.exception("Error fetching data for data_type=%s: %s", data_type, str(e))
                error_message = f"Error fetching data: {str(e)}"

        if request.GET.get('download') == 'true':
            logger.info("Download requested by user: %s", request.user.username)
            return excel_file_download()

    context = {
        'title': 'dataview',
        'data_type': data_type,
        **options,
        **dropdown_values,
        'selected_month': selected_month,
        'selected_year': selected_year,
        'error_message': error_message,
        'info_message': info_message,
        'tabs': tabs,
        'objects': objects,
        'html_summary_table': html_summary_table
    }
    logger.info("Rendering data_view page for user: %s", request.user.username)
    return render(request, "pages/data_view.html", context)

@login_required
@permission_required(get_permission_name("view"), raise_exception=True)
def download_data(request):
    """
    Handles the download of data based on the selected filters.
    """
    logger.info("Entered download_data for user: %s", request.user.username)

    data_type = request.GET.get('data_type')
    selected_month = to_int(request.GET.get('month'))
    selected_year = to_int(request.GET.get('year'))
    logger.debug("Download request: data_type=%s, month=%s, year=%s", data_type, selected_month, selected_year)

    if not data_type or not selected_month or not selected_year:
        logger.warning("Missing parameters for download: data_type=%s, month=%s, year=%s", data_type, selected_month, selected_year)
        return JsonResponse(
            serialize_error_response('Missing parameters for download', 400),
            status=400
        )
    
    client = get_api_client()
    file_stream, filename = client.download_file_stream(data_type, selected_month, selected_year)

    if file_stream:
        logger.info("data downloaded successfully")
        return FileResponse(file_stream, as_attachment=True, filename=filename)
    else:
        error_msg = f"Failed to fetch {data_type} file for month: {selected_month} year: {selected_year}"
        logger.error(f"Failed to fetch {data_type} file for {selected_month} {selected_year} - API error")
        return JsonResponse(
            serialize_error_response(error_msg, 404),
            status=404
        )


@login_required
def claims_capacity_report(request):
    # Exact URL you provided + rs:Embed=true
    print("started")
    src = settings.PBIRS_CLAIMS_CAPACITY_URL
    logger.info("Rendering report page for user: %s", request.user.username)
    # Optional: allow URL filtering via querystring (e.g., ?year=2025)
    year = request.GET.get("year")
    if year:
        sep = "&" if "?" in src else "?"
        src = f"{src}{sep}filter=DimDate/CalendarYear eq {int(year)}"

    return render(request, "pbi_frame.html", {"src": src})

@login_required
@permission_required(get_permission_name("view"), raise_exception=True)
def pbi_report(request, catalog_path:str):
    """
    Renders a Power BI report based on the provided catalog path.
    """
    logger.info("Entered pbi_report for user: %s", request.user.username)
    if not catalog_path:
        logger.warning("No catalog_path provided in request")
        return JsonResponse({'error': 'No catalog path provided'}, status=400)
    
    return 
    # Decode URL-encoded path
    decoded_path = urllib.parse.unquote(catalog_path)
    report_url = f"https://app.powerbi.com/reportEmbed?reportId={decoded_path}&autoAuth=true&ctid=72f988bf-86f1-41af-91ab-2d7cd011db47"
    
    context = {
        'title': 'Power BI Report',
        'report_url': report_url
    }
    logger.info("Rendering pbi_report page for user: %s with report_url: %s", request.user.username, report_url)
    return render(request, "pages/pbi_report.html", context)

@login_required
def redirect_to_allowed_view(request):
    """
    Checks a list of permissions and redirects the user to the first view
    for which they have the required permission.
    """
    # List of tuples: (permission_codename, URL name)
    # view_permissions = [
    #     ("forecast.upload_forecast_data", "forecast_upload"),
    #     ("forecast.view_forecast_list", "forecast_list"),
    #     ("catalogue.view_catalogue_list", "catalogue_list"),
    #     # Add more (permission, URL name) pairs as needed.
    # ]
    # for perm, url_name in view_permissions:
    #     if request.user.has_perm(perm):
    #         return redirect(url_name)
    # Fallback if no permissions match
    return redirect("forecast_app:employee_roster")

@permission_required(get_permission_name('add'), raise_exception=True)
def check_progress(request):
    file_upload_id = request.GET.get('file_upload_id')
    try:
        file_upload = UploadedFile.objects.get(id=file_upload_id)
        data = {
            'success': True,
            'progress': file_upload.progress,
            'status': file_upload.status,
        }
        return JsonResponse(data)
    except UploadedFile.DoesNotExist:
        return JsonResponse(
            serialize_error_response('Upload not found', 404),
            status=404
        )
    

def logout_view(request):
    logout(request)
    return redirect("forecast_app:login")
