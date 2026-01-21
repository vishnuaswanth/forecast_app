from django.shortcuts import redirect
class PermissionFallbackMiddleware:
   """
   Middleware that catches 403 responses (permission denied)
   and redirects authenticated users to a fallback view.
   """
   def __init__(self, get_response):
       self.get_response = get_response
   def __call__(self, request):
       response = self.get_response(request)
       # Check if the response is 403 and the user is authenticated.
       if response.status_code == 403 and request.user.is_authenticated:
           # Redirect the user to the fallback view.
           return redirect("../")
       return response