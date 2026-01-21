from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractUser, BaseUserManager

class UserManager(BaseUserManager):
    def create_user(self, portal_id, password=None, **extra_fields):
        """Create and return a regular user."""
        try:
            if not portal_id:
                raise ValueError("The portal_id field must be set")
            extra_fields.setdefault("is_active", True)
            user = self.model(portal_id=portal_id, **extra_fields)
            # Do NOT set a password since authentication is done via LDAP
            user.save(using=self._db)
            return user
        except Exception as e:
            print(f"the following error occured:{e}")
    
    def create_superuser(self, portal_id, password=None, **extra_fields):
        """Create and return a superuser."""
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        user = self.create_user(portal_id, **extra_fields)
        user.set_password(password)  # Only set password for superusers
        user.save(using=self._db)
        return user

class User(AbstractUser):
    portal_id = models.CharField(unique=True, max_length=10)
    email = models.EmailField(blank=True, null=True)
    
    objects = UserManager()

    USERNAME_FIELD = 'portal_id'
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.portal_id
    
    def save(self, *args, **kwargs):
        try:
            if not self.username:
                self.username = self.portal_id
            super().save(*args, **kwargs)
        except Exception as e:
            print(f"the following error occured:{e}")
        
    
User = get_user_model()


class UploadedFile(models.Model):
   file_data = models.BinaryField()
   filename = models.CharField(max_length=255)
   status = models.CharField(max_length=20, default='pending')
   progress = models.IntegerField(default=0)
   created_at = models.DateTimeField(auto_now_add=True)
   updated_at = models.DateTimeField(auto_now=True)
   def __str__(self):
       return f"Upload {self.id} - {self.status}"

