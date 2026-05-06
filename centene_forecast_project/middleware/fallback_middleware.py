from django.shortcuts import redirect
from django.contrib.auth import logout
from django.contrib import messages

class PermissionFallbackMiddleware:
   """
   Middleware that catches 403 responses (permission denied)
   and redirects authenticated users to the login page with an error message.
   """
   def __init__(self, get_response):
       self.get_response = get_response

   def __call__(self, request):
       response = self.get_response(request)
       if response.status_code == 403 and request.user.is_authenticated:
           logout(request)
           messages.error(request, "You do not have permission to access this application. Please contact your administrator.")
           return redirect("forecast_app:login")
       return response
