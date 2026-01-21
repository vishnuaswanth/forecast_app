import pandas as pd
from django.contrib import admin
from django.contrib.auth.models import Group
from django.contrib.auth import get_user_model
from django import forms
from django.contrib import messages
from django.db.models import Q
from django.http import HttpResponseForbidden
from django.shortcuts import redirect, render
from django.urls import path, reverse
from django.utils.html import format_html

from utils import *

User = get_user_model()

def render_user_upload_page(request, message=None, level="error", **kwargs):
    if message:
        message_func = getattr(messages, level, messages.error)
        message_func(request, message)
    return render(request, 'admin/user_upload.html', **kwargs)

class UserUploadForm(forms.Form):
    file = forms.FileField()


@admin.register(User)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ("portal_id", "first_name", "last_name", "email", "display_roles")
    search_fields = ("portal_id", "first_name", "last_name", "email")
    list_filter = ("groups",)
    ordering = ("portal_id",)
    actions = ["delete_selected"]
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path("upload-users/", self.admin_site.admin_view(self.upload_users), name="upload-users"),
        ]
        return custom_urls + urls
    
    def upload_users(self, request):
        if not (request.user.is_superuser or request.user.groups.filter(name__icontains="ADMIN").exists()):
            return HttpResponseForbidden("You do not have permission to access this page.")
        users_page_url = reverse("admin:core_user_changelist")

        """Handles user onboarding via Excel file upload."""
        if request.method == "POST" and request.FILES.get("file"):
            form = UserUploadForm(request.POST, request.FILES)
            if form.is_valid():
                file = request.FILES["file"]
                try:
                    if not is_excel_file(file.name):
                        render_user_upload_page(request,message=f"Invalid file type. Allowed: { ', '.join(EXCEL_FILETYPE)}")

                    df = pd.read_excel(file, sheet_name="user_data")
                    PORTAL_ID, ROLE = "Portal ID", "Role"
                    required_columns = {PORTAL_ID, ROLE}
                    if not required_columns.issubset(df.columns):
                        return render_user_upload_page(request,message="Invalid file format. Required columns: user_id, role")

                    for _, row in df.iterrows():
                        user, created = User.objects.get_or_create(portal_id=row[PORTAL_ID])
                        role_group = row[ROLE].strip()
                        # Assign user to appropriate role group
                        if role_group:
                            group, _ = Group.objects.get_or_create(name=role_group)
                            user.groups.set([group])
                            if 'ADMIN' in role_group:
                                user.is_staff = True
                        user.save()
                    messages.success(request, "Users uploaded successfully.")
                    return redirect(users_page_url)
                except Exception as e:
                    return render_user_upload_page(request,message=f"Error processing file: {e}")    
        return render_user_upload_page(request)  
    
    def display_roles(self, obj):
        """Displays assigned roles in the admin panel."""
        roles = [group.name for group in obj.groups.all()]
        return ", ".join(roles) if roles else "No Role Assigned"
    display_roles.short_description = "Roles"

    def bulk_upload_button(self):
       """
       Add a button for bulk user upload in Django Admin.
       """
       upload_url = reverse("admin:upload-users")  # Use URL name dynamically
       return format_html('<a class="button" href="{}" style="margin:10px; background:#28a745; color:white; padding:5px 10px; text-decoration:none; border-radius:5px; display: inline-block;">Bulk User Upload</a>', upload_url)
    
    def navigate_to_site(self):
       """
       Add a button for Navigate to site from Django Admin.
       """
       site_url = reverse("forecast_app:dataview")  # Use URL name dynamically
       return format_html('<a class="button" href="{}" style="margin:10px; background:#28a745; color:white; padding:5px 10px; text-decoration:none; border-radius:5px; display: inline-block;">Go to site </a>', site_url)
    
    def changelist_view(self, request, extra_context=None):
        """
        Modify the Users list page in Django Admin to include a bulk upload button.
        """
        extra_context = extra_context or {}
        extra_context["bulk_upload_button"] = self.bulk_upload_button()
        extra_context["navigate_to_site"] = self.navigate_to_site()
        return super().changelist_view(request, extra_context=extra_context)

    def get_form(self, request, obj=None, **kwargs):
        """Dynamically restrict role assignments based on logged-in user's app-specific role."""
        form = super().get_form(request, obj, **kwargs)
        if obj:
            form.base_fields.pop("password", None)
        if request.user.is_superuser:
            return form
        user_groups = request.user.groups.values_list("name", flat=True)
        allowed_groups_qs = self.get_allowed_groups_queryset(user_groups)
        # print(allowed_groups)
        form.base_fields["groups"].queryset = allowed_groups_qs
        return form
    
    def get_allowed_groups_queryset(self, user_groups):
        """Extracts app-specific roles dynamically from user groups."""
        app_names = set()

        # Extract app names from user groups with "ADMIN"
        for group_name in user_groups:
            parts = group_name.split("_")
            if parts[-1] == "ADMIN":
                app_name = "_".join(parts[:-1])
                app_names.add(app_name)

        # Using Q objects to filter groups based on collected app names
        if app_names:
            query = Q()
            for app_name in app_names:
                query |= Q(name__icontains=app_name)

            filtered_groups_qs = Group.objects.filter(query)
        else:
            filtered_groups_qs = Group.objects.none()
        return filtered_groups_qs
    
# admin.site.register(User, CustomUserAdmin)
