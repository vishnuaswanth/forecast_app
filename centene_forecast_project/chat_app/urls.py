from django.urls import path
from . import views

app_name = "chat_app"

urlpatterns = [
    path("download-ramp-excel/", views.download_ramp_excel, name="download_ramp_excel"),
    path("toggle-widget/", views.toggle_chat_widget, name="toggle_chat_widget"),
]
