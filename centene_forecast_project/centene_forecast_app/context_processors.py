from django.contrib.auth import get_user_model
from utils import *

User = get_user_model()

def user_profile_name(request):
    """Returns the full name of the logged-in user as user_name."""
    if request.user.is_authenticated:
        full_name = f"{request.user.first_name} {request.user.last_name}".strip()
        return {
            "user_name": full_name if full_name else request.user.username,
            "is_staff": request.user.is_staff or False
        }
    return {"user_name": "", "is_staff": False}

def user_timezone_name(request):
    if 'timezone' in request.session:
        time_zone = request.session.get('timezone')
        utcoffset, is_daylight_saving, tz_abbreviation, tz_fullname = get_timezone_info(time_zone)
        return {
            "timezone": time_zone,
            "utcoffset": utcoffset,
            "is_daylight_saving": is_daylight_saving,
            "tz_abbreviation": tz_abbreviation,
            "tz_fullname": tz_fullname,
        }
    return {
        "timezone": "",
        "utcoffset": "",
        "is_daylight_saving": "",
        "tz_abbreviation": "",
        "tz_fullname": "",
    }

def combined_context(request):
    context = {}
    context.update(user_profile_name(request))
    context.update(user_timezone_name(request))
    return context
