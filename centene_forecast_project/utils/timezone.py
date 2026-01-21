import pytz
import datetime

def get_timezone_info(tz_name):
    """
    Given an IANA timezone name, returns a tuple (utcoffset_formatted, is_daylight_saving)
    where utcoffset_formatted is a string like "-06:00:00" and is_daylight_saving is a boolean.
    """
    tz = pytz.timezone(tz_name)
    now = datetime.datetime.now(tz)
    offset_timedelta = now.utcoffset() or datetime.timedelta(0)
    offset_seconds = int(offset_timedelta.total_seconds())
    sign = '+' if offset_seconds >= 0 else '-'
    offset_seconds = abs(offset_seconds)
    hours = offset_seconds // 3600
    minutes = (offset_seconds % 3600) // 60
    seconds = offset_seconds % 60
    utcoffset_formatted = "{}{:02d}:{:02d}:{:02d}".format(sign, hours, minutes, seconds)
    
    # Determine if DST is active
    is_daylight_saving = bool(now.dst() and now.dst() != datetime.timedelta(0))
    
    # Use a static abbreviation as per your requirement.
    tz_abbreviation = "UTC"
    
    # Map IANA timezone names to their expanded names.
    # You can extend this mapping as needed.
    IANA_TO_FULLNAME = {
        "America/Chicago": "Central Standard Time",
        "America/New_York": "Eastern Standard Time",
        "Asia/Kolkata": "Indian Standard Time",
    }
    tz_fullname = IANA_TO_FULLNAME.get(tz_name, tz_name)  # Fallback to tz_name if not found.
    
    return utcoffset_formatted, is_daylight_saving, tz_abbreviation, tz_fullname
