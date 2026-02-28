from cloudinary.models import CloudinaryField
from django.contrib.auth.models import AbstractUser
from django.db import models

class UserRole(models.TextChoices):
    ADMIN = "ADMIN", "Admin"
    STAFF = "STAFF", "Staff"
    CUSTOMER = "CUSTOMER", "Khách hàng"

class User(AbstractUser):
    full_name = models.CharField(max_length=100)
    avatar = CloudinaryField(null=True, blank=True)
    email = models.EmailField(max_length=255, unique=True, blank=True)
    address = models.CharField(max_length=255, null=True)
    birth = models.IntegerField(null=True)
    user_role = models.CharField(max_length=10, default=UserRole.CUSTOMER, choices=UserRole.choices)

    def __str__(self):
        return self.full_name