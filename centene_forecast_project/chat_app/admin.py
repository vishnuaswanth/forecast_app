from django.contrib import admin

from chat_app.models import ChatWidgetSetting


@admin.register(ChatWidgetSetting)
class ChatWidgetSettingAdmin(admin.ModelAdmin):
    list_display = ("is_enabled", "updated_by", "updated_at")
    readonly_fields = ("updated_by", "updated_at")

    def has_add_permission(self, request):
        # Singleton row only.
        return not ChatWidgetSetting.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
