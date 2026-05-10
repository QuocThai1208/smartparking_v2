from cloudinary.models import CloudinaryField
from django.contrib.auth.models import AbstractUser
from django.db import models


class UserRole(models.TextChoices):
    ADMIN = "ADMIN", "Quản trị viên"
    MANAGE = "MANAGE", "Quản lý"
    STAFF = "STAFF", "Nhận viên"
    CUSTOMER = "CUSTOMER", "Khách hàng"


class EmployeePosition(models.TextChoices):
    OPERATOR = 'OPERATOR', 'Giám sát vận hành'
    TECHNICAL = 'TECHNICAL', 'Kỹ thuật viên'
    MARSHAL = 'MARSHAL', 'Điều phối'
    INCIDENT = 'INCIDENT', 'Xử lý sự cố'


class JobPosition(models.Model):
    title = models.CharField(choices=EmployeePosition.choices, max_length=10, unique=True)
    description = models.TextField(null=True, blank=True)
    base_salary = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return self.title


class User(AbstractUser):
    full_name = models.CharField(max_length=100)
    avatar = CloudinaryField(null=True, blank=True)
    email = models.EmailField(max_length=255, unique=True)
    address = models.CharField(max_length=255, null=True)
    birth = models.IntegerField(null=True)
    user_role = models.CharField(max_length=10, default=UserRole.CUSTOMER, choices=UserRole.choices)

    def __str__(self):
        return self.full_name


class EmployeeProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    parking_lot = models.ForeignKey('parking.ParkingLot', on_delete=models.CASCADE)
    job_position = models.ForeignKey(JobPosition, on_delete=models.CASCADE)
