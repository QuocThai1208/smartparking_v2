from django.utils import timezone

from cloudinary.models import CloudinaryField
from django.db import models
from ..users.models import User

class ParkingStatus(models.TextChoices):
    IN = "IN", "Đang gửi"
    OUT = "OUT", "Đã lấy xe"

class FeeType(models.TextChoices):
    MOTORCYCLE = "MOTORCYCLE", "Xe máy"
    CAR = "CAR", "Ô tô"


class BaseModel(models.Model):
    active = models.BooleanField(default=True)
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ['-id']


class FeeRule(BaseModel):
    fee_type = models.CharField(max_length=10, choices=FeeType.choices)
    amount = models.PositiveIntegerField(help_text="Giá (VNĐ)")
    effective_from = models.DateField(default=timezone.localdate)
    effective_to = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.fee_type} ({self.amount}đ)"


class Vehicle(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="vehicles")
    name = models.CharField(max_length=255, help_text="Tên/đời xe – ví dụ: Yamaha Sirius")
    license_plate = models.CharField(max_length=15, unique=True, help_text="Biển số xe")
    image = CloudinaryField(null=True, blank=True, help_text="Ảnh xe")
    vehicle_type = models.CharField(max_length=20, choices=FeeType.choices)
    is_approved = models.BooleanField(default=False, help_text="Đã được admin duyệt chưa")

    def __str__(self):
        return self.license_plate


class ParkingLog(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="parking_logs")
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name="parking_logs")
    fee_rule = models.ForeignKey(FeeRule, on_delete=models.CASCADE, related_name="parking_logs")
    check_in = models.DateTimeField(default=timezone.now)
    check_out = models.DateTimeField(null=True, blank=True)
    duration_minutes = models.PositiveIntegerField(editable=False, null=True, blank=True)
    fee = models.PositiveIntegerField(null=True, blank=True, help_text="Phí phải trả cho lượt này")
    status = models.CharField(max_length=4, choices=ParkingStatus.choices, default=ParkingStatus.IN)

    def save(self, *args, **kwargs):
        if self._state.adding:
            self.fee_value = self.fee_rule.amount
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Log {self.id} - {self.vehicle.license_plate}"
