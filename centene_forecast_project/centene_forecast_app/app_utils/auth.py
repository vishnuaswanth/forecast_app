from django.contrib.auth import get_user_model

from utils import get_app_name

User = get_user_model()

APP_NAME = get_app_name(__name__)
PERMISSION_PREFIX = "auth"

def get_permission_name(permission_label:str)-> str:
    """Returns permission name from permisson_label values, It takes values such as 'view','edit','add','delete','admin' """
    return f"{PERMISSION_PREFIX}.{permission_label}_{APP_NAME}"

