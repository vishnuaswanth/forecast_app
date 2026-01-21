from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth import get_user_model

class Command(BaseCommand):
    help = "Creates role groups and permissions dynamically for an app"
    def add_arguments(self, parser):
        parser.add_argument("app_label", type=str, help="The app label")

    def handle(self, *args, **options):
        app_label:str = options["app_label"]
        view_perm, _ = Permission.objects.get_or_create(
            codename=f"view_{app_label}",
            name=f"Can view in {app_label}",
            content_type=ContentType.objects.get_for_model(Permission)
        )
        add_perm, _ = Permission.objects.get_or_create(
            codename=f"add_{app_label}",
            name=f"Can add in {app_label}",
            content_type=ContentType.objects.get_for_model(Permission)
        )
        edit_perm, _ = Permission.objects.get_or_create(
            codename=f"edit_{app_label}",
            name=f"Can edit in {app_label}",
            content_type=ContentType.objects.get_for_model(Permission)
        )
        delete_perm, _ = Permission.objects.get_or_create(
            codename=f"delete_{app_label}",
            name=f"Can delete in {app_label}",
            content_type=ContentType.objects.get_for_model(Permission)
        )
        admin_perm, _ = Permission.objects.get_or_create(
            codename=f"admin_{app_label}",
            name=f"Can administer in {app_label}",
            content_type=ContentType.objects.get_for_model(Permission)
        )
        User = get_user_model()
        custom_user_content_type = ContentType.objects.get_for_model(User)
        admin_user_permissions = Permission.objects.filter(content_type=custom_user_content_type)
        groups = {
            f"{app_label.upper()}_VIEWER": [view_perm],
            f"{app_label.upper()}_EDITOR": [view_perm, add_perm ,edit_perm],
            f"{app_label.upper()}_ADMIN": [view_perm, add_perm, edit_perm, delete_perm, admin_perm, *admin_user_permissions],
        }
        for group_name, perms in groups.items():
            group, created = Group.objects.get_or_create(name=group_name)
            group.permissions.set(perms)
        self.stdout.write(self.style.SUCCESS(f"Roles created for {app_label}"))