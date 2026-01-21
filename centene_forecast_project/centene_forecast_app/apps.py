from django.apps import AppConfig
from django.contrib import admin
from django.urls import reverse, NoReverseMatch
import logging
import atexit

logger = logging.getLogger('django')

class CenteneForecastAppConfig(AppConfig):
    """
    Configuration for Centene Forecast application.
    
    Registers shutdown handlers to close API connections gracefully
    when Django application stops.
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'centene_forecast_app'

    def ready(self):
        """
        Called when Django starts.
        
        - Registers cleanup handlers for graceful shutdown
        - Initializes any required app-level resources
        """
        logger.info("Centene Forecast app initializig ...")
        # Set admin site url
        try:
            admin.site.site_url = reverse('forecast_app:dataview')
        except NoReverseMatch:
            admin.site.site_url = "/"
        # Register graceful shutdown handler
        self._register_shutdown_handler()
        logger.info("Centene Forecast app ready")

    def _register_shutdown_handler(self):
        """
        Register cleanup function to run on application exit.
        
        Uses atexit to ensure API connections are closed gracefully
        when Django shuts down (both development and production).
        """
        from centene_forecast_app.repository import reset_api_client

        def cleanup():
            """
            Cleanup function called on application shutdown.
            
            Closes API client connections and clears singleton reference.
            """
            try:
                reset_api_client()
                logger.info("[OK] API client closed gracefully on shutdown")
            except Exception as e:
                logger.error(f"[ERROR] Error during API client cleanup: {e}")

        # Register cleanup to run at exit
        atexit.register(cleanup)
        logger.debug("Registered atexit handler for API client cleanup")
