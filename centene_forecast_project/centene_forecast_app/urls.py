from django.urls import path

from centene_forecast_app import views
from centene_forecast_app.views import cache_views, execution_monitoring, edit_view, configuration_view

app_name = "forecast_app"

urlpatterns = [
    path('', views.login_view, name='login'),
    path('fallback/', views.redirect_to_allowed_view, name="fallback"),
    path('check_upload_progress/', views.check_progress, name='upload_progress'),

    path('timezone/', views.timezone_selection, name='time_zone'),
    # path('home/', views.home_view, name='home'),

    path('forecast_table_data/', views.forecast_data_table, name='forecast_table_data'),
    path('roster_table_data/<str:roster_type>/', views.roster_data_table, name='roster_table_data'),
    path('actuals_table_data/', views.actuals_data_table, name='actuals_table_data'),

    path('download_data/', views.download_data, name='data_download'),

    path('upload_view/', views.upload_view, name='upload'),
    path('data_view/', views.data_view, name='dataview'),

    # Forecast cascade API endpoints
    path('forecast/filter-years/', views.forecast_filter_years_api, name='forecast_filter_years'),
    path('forecast/months/', views.forecast_months_api, name='forecast_months'),
    path('forecast/platforms/', views.forecast_platforms_api, name='forecast_platforms'),
    path('forecast/markets/', views.forecast_markets_api, name='forecast_markets'),
    path('forecast/localities/', views.forecast_localities_api, name='forecast_localities'),
    path('forecast/worktypes/', views.forecast_worktypes_api, name='forecast_worktypes'),

    # Centene Forecasting Power BI Report Endpoints
    # path('reports/<path:catalog_path>/', views.pbi_report, name='pbi_report'),
    path("reports/claims-capacity/", views.claims_capacity_report, name="claims-capacity"),

    path("manager-view/", views.manager_view_page, name="manager_view_page"),
    path("api/manager-view/data/", views.manager_view_data_api, name="manager_view_data"),
    path("api/manager-view/kpi/", views.manager_view_kpi_api, name="manager_view_kpi"),

    # Execution Monitoring endpoints
    path("execution-monitoring/", execution_monitoring.execution_monitoring_page, name="execution_monitoring_page"),
    path("api/execution-monitoring/list/", execution_monitoring.execution_list_api, name="execution_list"),
    path("api/execution-monitoring/details/<str:execution_id>/", execution_monitoring.execution_details_api, name="execution_details"),
    path("api/execution-monitoring/kpis/", execution_monitoring.execution_kpis_api, name="execution_kpis"),
    path("api/execution-monitoring/download/<str:execution_id>/<str:report_type>/", execution_monitoring.download_execution_report_api, name="download_execution_report"),
    path("api/execution-monitoring/health/", execution_monitoring.execution_monitoring_health, name="execution_monitoring_health"),

    # Edit View endpoints
    path("edit-view/", edit_view.edit_view_page, name="edit_view_page"),
    path("api/edit-view/allocation-reports/", edit_view.allocation_reports_api, name="allocation_reports"),
    path("api/edit-view/bench-allocation/preview/", edit_view.bench_allocation_preview_api, name="bench_allocation_preview"),
    path("api/edit-view/bench-allocation/update/", edit_view.bench_allocation_update_api, name="bench_allocation_update"),
    path("api/edit-view/history-log/", edit_view.history_log_api, name="history_log"),
    path("api/edit-view/history-log/<str:history_log_id>/download/", edit_view.download_history_excel_api, name="download_history_excel"),

    # Forecast Reallocation endpoints
    path("api/edit-view/forecast-reallocation/filters/", edit_view.forecast_reallocation_filters_api, name="forecast_reallocation_filters"),
    path("api/edit-view/forecast-reallocation/data/", edit_view.forecast_reallocation_data_api, name="forecast_reallocation_data"),
    path("api/edit-view/forecast-reallocation/preview/", edit_view.forecast_reallocation_preview_api, name="forecast_reallocation_preview"),
    path("api/edit-view/forecast-reallocation/update/", edit_view.forecast_reallocation_update_api, name="forecast_reallocation_update"),

    # Cache Management API endpoints
    path('api/cache/stats/', cache_views.cache_stats_view, name='cache_stats'),
    path('api/cache/inspect/', cache_views.inspect_cache_view, name='cache_inspect'),
    path('api/cache/config/', cache_views.cache_config_view, name='cache_config'),
    path('api/cache/clear/forecast/', cache_views.clear_forecast_cache_view, name='clear_forecast_cache'),
    path('api/cache/clear/roster/', cache_views.clear_roster_cache_view, name='clear_roster_cache'),
    path('api/cache/clear/summary/', cache_views.clear_summary_cache_view, name='clear_summary_cache'),
    path('api/cache/clear/cascade/', cache_views.clear_cascade_caches_view, name='clear_cascade_caches'),
    path('api/cache/clear/all/', cache_views.clear_all_caches_view, name='clear_all_caches'),

    # Configuration View endpoints
    path("configuration/", configuration_view.configuration_view_page, name="configuration_view_page"),

    # Month Configuration APIs
    path("api/configuration/month-config/", configuration_view.month_config_list_api, name="month_config_list"),
    path("api/configuration/month-config/create/", configuration_view.month_config_create_api, name="month_config_create"),
    path("api/configuration/month-config/bulk/", configuration_view.month_config_bulk_create_api, name="month_config_bulk_create"),
    path("api/configuration/month-config/<int:config_id>/", configuration_view.month_config_update_api, name="month_config_update"),
    path("api/configuration/month-config/<int:config_id>/delete/", configuration_view.month_config_delete_api, name="month_config_delete"),
    path("api/configuration/month-config/validate/", configuration_view.month_config_validate_api, name="month_config_validate"),

    # Target CPH Configuration APIs
    path("api/configuration/target-cph/", configuration_view.target_cph_list_api, name="target_cph_list"),
    path("api/configuration/target-cph/create/", configuration_view.target_cph_create_api, name="target_cph_create"),
    path("api/configuration/target-cph/bulk/", configuration_view.target_cph_bulk_create_api, name="target_cph_bulk_create"),
    path("api/configuration/target-cph/<int:config_id>/", configuration_view.target_cph_update_api, name="target_cph_update"),
    path("api/configuration/target-cph/<int:config_id>/delete/", configuration_view.target_cph_delete_api, name="target_cph_delete"),
    path("api/configuration/target-cph/distinct/main-lobs/", configuration_view.target_cph_distinct_lobs_api, name="target_cph_distinct_lobs"),
    path("api/configuration/target-cph/distinct/case-types/", configuration_view.target_cph_distinct_case_types_api, name="target_cph_distinct_case_types"),

    path('logout/', views.logout_view, name='logout'),
] 