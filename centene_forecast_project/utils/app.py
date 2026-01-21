from django.apps import apps

def get_app_name(name:str=None)->str|None:
    for app_config in apps.get_app_configs():
        if name.startswith(app_config.name):
            return app_config.name
    return None
    