# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Centene Forecasting is a Django-based web application for workforce capacity planning. It processes forecast data and roster information to calculate required case handlers (agents), providing insights through multiple dashboards. The system integrates with an external FastAPI backend via a repository pattern and uses LDAP authentication for NTT Data corporate environment.

## Development Commands

### Initial Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Navigate to Django project directory
cd centene_forecast_project

# Run database migrations
python manage.py migrate

# Create superuser (for local development)
python manage.py createsuperuser

# Collect static files
python manage.py collectstatic --noinput
```

### Running the Application
```bash
# Start development server (from centene_forecast_project directory)
python manage.py runserver

# Start Django-Q worker for background tasks (separate terminal)
python manage.py qcluster

# Access the application
# http://127.0.0.1:8000/
```

### Database Management
```bash
# Create new migrations after model changes
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Access Django shell
python manage.py shell

# Reset database (development only)
rm db.sqlite3
python manage.py migrate
```

### Maintenance Commands
```bash
# Clear expired cache entries
python manage.py clearcache

# Check deployment readiness
python manage.py check --deploy
```

## Architecture Overview

### Application Structure

The project follows a layered architecture pattern with clear separation of concerns:

**centene_forecast_app** - Main application containing:
- **views/** - HTTP request handlers (5 modules: core views, manager view, execution monitoring, edit view, cache management)
- **services/** - Business logic layer (dataview, manager, execution, edit services)
- **serializers/** - JSON response formatting (matching service layer)
- **validators/** - Input validation before passing to services
- **app_utils/** - Helper utilities (auth, caching, file handling, table utilities)
- **repository.py** - API client abstracting FastAPI backend (1,583 lines, singleton pattern)

**core** - Authentication and configuration:
- Custom User model with LDAP integration (`portal_id` as USERNAME_FIELD)
- UploadedFile model for async file processing tracking
- LDAPBackend for NTT Data authentication (ldap://americas.global.nttdata.com)
- Configuration classes (ManagerViewConfig, ForecastCacheConfig, ExecutionMonitoringConfig, EditViewConfig)

**middleware** - Custom request processing:
- PermissionFallbackMiddleware catches 403 errors and redirects authenticated users

**utils** - Global utilities (timezone handling, file validation, app name detection)

### Data Flow Pattern

The application does NOT have traditional Django models for business data. Instead:

1. **Repository Pattern**: `APIClient` class in `repository.py` abstracts all backend communication
2. **External Backend**: FastAPI server at `http://127.0.0.1:8888` (configured in settings.py as `API_BASE_URL`)
3. **Data Flow**: Views → Services → Validators → Repository → FastAPI Backend

Example flow:
```
User request → data_view()
  → ForecastFilterService.get_months_for_year(year)
  → ForecastValidator.validate_year(year)
  → APIClient.get_all_forecast_records(...)
  → HTTP GET to FastAPI backend
  ← JSON response
  → ForecastSerializer.serialize_cascade_response()
  ← JSON to frontend
```

### Authentication & Authorization

**LDAP Authentication**:
- Backend: `core.backends.LDAPBackend`
- Server: ldap://americas.global.nttdata.com
- Bind format: `AMERICAS\{username}`
- Base DN: `OU=Employees,DC=AMERICAS,DC=GLOBAL,DC=NTTDATA,DC=COM`
- Fetches: CN, givenName, sn, mail

**Permission System**:
```python
# Permissions follow the pattern: auth.{action}_centene_forecast_app
# Available actions: view, add, edit, admin

# Standard decorator stack on views:
@login_required
@permission_required('auth.view_centene_forecast_app', raise_exception=True)
@require_http_methods(["GET"])
def view_function(request):
    pass
```

Users must be assigned to Django Groups (ADMIN, MANAGER, VIEWER) via Django admin. The LDAP backend validates credentials and checks group membership on each login.

### Caching Strategy

Three-tier cache architecture (configured in settings.py):

1. **locmem** (default) - Fast in-memory cache for single-process development
2. **filebased** - Persistent cache stored in `centene_forecast_project/cache_files/`
3. **Redis** (optional) - For production multi-worker environments

**Cache TTLs** (from `core/config.py`):
- Cascade filters (years/months/platforms): 300s (5 min)
- Data tables (forecast/roster records): 900s (15 min)
- Schema metadata: 900s (15 min)
- Manager view data: 900s (15 min)
- Execution list: 30s (real-time feedback)
- Execution details (in progress): 5s
- Execution details (completed): 3600s (1 hour)

**Cache Management**:
```python
# Decorator pattern in app_utils/cache_utils.py
@cache_with_ttl(ttl=300, key_prefix='forecast')
def fetch_data():
    pass

# Invalidation functions (used after file uploads):
clear_forecast_cache()      # Clears forecast:* pattern
clear_roster_cache()        # Clears roster:* pattern
clear_cascade_caches()      # Clears filter dropdowns
clear_all_caches()          # Nuclear option
```

Cache statistics available at `/api/cache/stats/` for monitoring hit/miss rates.

### File Upload Processing

**Async Upload Flow**:
1. User uploads CSV/Excel file via `/upload/` endpoint
2. View validates file type and reads content
3. `APIClient.upload_*_file()` sends to FastAPI backend with retry logic (Retry with exponential backoff)
4. Django-Q processes file in background (configured with 4 workers, 60s timeout)
5. Progress tracked in `UploadedFile` model (0-100%)
6. WebSocket (`/ws/up/`) streams real-time progress to frontend
7. Cache invalidation triggered on success

**Supported Upload Types**:
- Roster files (roster_file)
- Forecast files (forecast_file)
- Altered forecast (altered_forecast_file)
- Prod team roster (prod_team_roster_file)

**Excel Sheet Naming**: For Excel files, the system uses pattern matching to find the correct sheet (e.g., "Dec'2024" format).

### Frontend Integration

**JavaScript Stack**:
- jQuery 3.7.1 - DOM manipulation and AJAX
- DataTables - Server-side pagination for large datasets
- DataTables Editor - Inline editing
- Select2 4.0.6 - Searchable dropdowns
- SweetAlert2 11.15.0 - User-friendly alerts

**Templates**:
- Base template: `templates/base.html` with navigation
- App templates: `centene_forecast_app/templates/centene_forecast_app/`
- Context processor injects user info and timezone data into all templates

**Static Files**:
- Managed by WhiteNoise with compression
- Located in `static/` (development) and `staticfiles/` (production)
- CSS, JS, and images organized by type

### WebSocket Support

**Configuration**:
- ASGI application with Django Channels
- WebSocket routing in `centene_forecast_app/routing.py`
- `TestConsumer` handles real-time upload progress
- Endpoint: `/ws/up/`

**Usage**: Frontend connects to WebSocket after initiating file upload to receive progress updates in real-time.

## Key Configuration Files

### settings.py Important Settings

```python
# Custom user model
AUTH_USER_MODEL = 'core.User'

# LDAP authentication
LDAP_AUTH_URL = "ldap://americas.global.nttdata.com"
AUTHENTICATION_BACKENDS = [
    'core.backends.LDAPBackend',
    'django.contrib.auth.backends.ModelBackend',
]

# External API backend
API_BASE_URL = "http://127.0.0.1:8888"

# Django-Q background tasks
Q_CLUSTER = {
    "name": "DjangoQ",
    "workers": 4,
    "timeout": 60,
    "queue_limit": 50,
    "bulk": 10,
    "orm": "default",
}

# Caching
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'forecast-cache',
    },
    'filebased': {
        'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache',
        'LOCATION': os.path.join(BASE_DIR, 'cache_files'),
    },
}
```

### core/config.py Business Configuration

**ManagerViewConfig**:
- `MONTHS_TO_DISPLAY = 6` - Forecast months shown in manager dashboard
- `KPI_MONTH_INDEX = 1` - Which month to use for KPI summary cards (0-indexed)
- `MAX_HIERARCHY_DEPTH = 6` - Category tree depth limit
- `ENABLE_SEARCHABLE_DROPDOWNS = True` - Use Select2 for filters

**ForecastCacheConfig**:
- `CASCADE_TTL = 300` - Filter dropdown cache (5 min)
- `DATA_TTL = 900` - Record data cache (15 min)
- `SCHEMA_TTL = 900` - Schema metadata cache (15 min)
- `SUMMARY_TTL = 900` - Pre-rendered HTML table cache (15 min)

**ExecutionMonitoringConfig**:
- `INITIAL_PAGE_SIZE = 100` - First load records
- `LAZY_LOAD_PAGE_SIZE = 100` - Pagination size
- `HERO_REFRESH_INTERVAL = 5000` - KPI auto-refresh (ms)

## Common Workflows

### Adding a New View/Endpoint

1. Create view function in appropriate module (`views/`, `manager_view.py`, etc.)
2. Add service function in corresponding `services/` module
3. Create serializer method in `serializers/` module
4. Add validator in `validators/` module
5. Update URL routing in `centene_forecast_app/urls.py`
6. If using repository, add method to `APIClient` class in `repository.py`
7. Add caching decorator if needed (`@cache_with_ttl`)
8. Test permission decorators (`@permission_required`)

### Modifying Cache Behavior

1. Update TTL constants in `core/config.py` (ForecastCacheConfig, etc.)
2. Modify cache decorator in `app_utils/cache_utils.py` if changing logic
3. Add new cache invalidation function if needed (follow `clear_*_cache()` pattern)
4. Update cache invalidation calls in file upload views

### Adding New File Upload Type

1. Add upload type to `upload_view()` in `centene_forecast_app/views/views.py`
2. Create corresponding `APIClient.upload_*_file()` method in `repository.py`
3. Update cache invalidation strategy (which caches to clear)
4. Add file type validation if needed
5. Update frontend upload form to include new type option

### Working with Cascading Filters

The application uses cascading dropdowns for data filtering (year → month → platform → market → locality → worktype).

**Backend**:
- Service: `ForecastFilterService` in `services/dataview_service.py`
- Validators: `dataview_validators.py`
- Endpoints follow pattern: `/forecast/filter-years/`, `/forecast/months/`, etc.

**Frontend**:
- JavaScript handles dependent dropdown updates
- Uses Select2 for searchable dropdowns
- Filters cascade from left to right (each selection limits next dropdown)

To add a new filter level, update the service to fetch from repository and add endpoint in URLs.

## Important Notes

### LDAP Authentication Requirements

- Production requires access to NTT Data LDAP server
- Development: Use `python manage.py createsuperuser` to create local admin (bypasses LDAP)
- Users must have at least one group assigned to access the application
- Group membership controls permissions (not individual user permissions)

### FastAPI Backend Dependency

This Django application is a **frontend** for an external FastAPI backend. The backend must be running at `http://127.0.0.1:8888` (or update `API_BASE_URL` in settings.py).

**Repository Pattern**: All database operations go through `APIClient` in `repository.py`. Do NOT attempt to create Django ORM models for business data (roster, forecast, etc.) - these exist in the FastAPI backend.

### Django-Q Background Processing

File uploads and long-running tasks use Django-Q for async processing:
- Start worker: `python manage.py qcluster`
- Tasks defined in `centene_forecast_app/tasks.py`
- Progress tracked in `UploadedFile` model
- WebSocket provides real-time updates to frontend

Without running qcluster, file uploads will not be processed.

### Static Files in Production

WhiteNoise serves static files efficiently:
- Run `python manage.py collectstatic` before deployment
- Uses compressed and hashed filenames (CompressedManifestStaticFilesStorage)
- No need for separate nginx/Apache static file serving

### Database Migrations

Only `core` app has Django models:
- `User` - Custom user with LDAP integration
- `UploadedFile` - File upload progress tracking

All other data lives in the FastAPI backend and is accessed via `repository.py`.

### Security Considerations

- **SECRET_KEY**: Currently hardcoded - use environment variable in production
- **DEBUG**: Set to False in production
- **ALLOWED_HOSTS**: Add production domains
- **LDAP credentials**: Never logged or stored (validated against LDAP server directly)
- **CSRF protection**: Enabled via Django middleware
- **File uploads**: Validated for type before processing (CSV and XLSX only)
