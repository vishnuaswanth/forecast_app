from django.shortcuts import redirect
from django.contrib.auth import logout
from django.contrib import messages


def _is_api_request(request):
    """
    Detect AJAX/API calls so a permission-denied response on a single action
    (e.g. clicking Delete without admin rights) doesn't log the user out of
    the whole app. Real page navigations should still get the logout+redirect.
    """
    if request.path.startswith('/api/'):
        return True
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return True
    accept = request.headers.get('Accept', '')
    if 'application/json' in accept and 'text/html' not in accept:
        return True
    return False


class PermissionFallbackMiddleware:
   """
   Middleware that catches 403 responses (permission denied) on page
   navigations and redirects authenticated users to the login page with an
   error message. API/AJAX requests are left alone so callers get a normal
   403 response instead of being silently logged out.
   """
   def __init__(self, get_response):
       self.get_response = get_response

   def __call__(self, request):
       response = self.get_response(request)
       if response.status_code == 403 and request.user.is_authenticated and not _is_api_request(request):
           logout(request)
           messages.error(request, "You do not have permission to access this application. Please contact your administrator.")
           return redirect("forecast_app:login")
       return response
