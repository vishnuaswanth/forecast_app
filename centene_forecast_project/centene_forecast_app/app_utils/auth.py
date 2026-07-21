from django.contrib.auth import get_user_model

from utils import get_app_name

User = get_user_model()

APP_NAME = get_app_name(__name__)
PERMISSION_PREFIX = "auth"

def get_permission_name(permission_label:str)-> str:
    """Returns permission name from permisson_label values, It takes values such as 'view','edit','add','delete','admin' """
    return f"{PERMISSION_PREFIX}.{permission_label}_{APP_NAME}"

def get_display_name(user) -> str:
    """Returns the user's full name (from LDAP first_name/last_name) for audit
    fields like created_by/updated_by, falling back to portal_id (username) when
    names aren't populated - e.g. local superusers created via createsuperuser,
    which bypasses LDAP."""
    full_name = f"{user.first_name} {user.last_name}".strip()
    return full_name if full_name else user.username

