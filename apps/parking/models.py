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
    TRUCK = "TRUCK", "Xe tải"
    BUS = "BUS", "Xe bus"


class BookingStatus(models.TextChoices):
    PENDING = "PENDING", "Chờ thanh toán cọc",
    CONFIRMED = "CONFIRMED", "Đã đặt chỗ thành công",
    CHECKED_IN = "CHECKED_IN", "Đã vào bãi",
    CANCELLED = "CANCELLED", "Khách hàng hủy",
    EXPIRED = "EXPIRED", "Quán hạn không đến (mất cọc)"


class BaseModel(models.Model):
    active = models.BooleanField(default=True)
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ['-id']


class ParkingLot(BaseModel):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="parking_slots")
    name = models.CharField(max_length=255)
    address = models.CharField(max_length=255)
    latitude = models.FloatField()
    longitude = models.FloatField()
    total_slots = models.PositiveIntegerField()
    image = CloudinaryField(null=True, blank=True)

    # Ngưỡng hạ rào tự động
    threshold_release = models.FloatField(default=0.8)


    def __str__(self):
        return self.name


class FeeRule(BaseModel):
    fee_type = models.CharField(max_length=10, choices=FeeType.choices)
    parking_lot = models.ForeignKey(ParkingLot, on_delete=models.CASCADE, related_name="fee_rules")
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
    is_approved = models.BooleanField(default=False, help_text="Đã được admin duyệt chưa")
    type = models.CharField(max_length=20, choices=FeeType.choices)
    color = models.CharField(max_length=20, null=True, blank=True)  # Ví dụ: "Red", "Black"
    brand = models.CharField(max_length=50, null=True, blank=True)  # Ví dụ: "Honda"

    def __str__(self):
        return self.license_plate


class VehicleFace(BaseModel):
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='faces')
    owner_name = models.CharField(max_length=100, verbose_name="Tên người lái")
    relationship = models.CharField(max_length=10, verbose_name="Quan hệ với chủ xe")
    face_img = CloudinaryField()
    face_vector = models.JSONField(verbose_name="Vector đặc trưng")
    is_default = models.BooleanField(default=False)
    parent = models.ForeignKey('self', null=True, blank=True, related_name='children', on_delete=models.SET_NULL)

    class Meta:
        ordering = ['-is_default']

    def __str__(self):
        return f"{self.vehicle.name} - {self.owner_name}"


class ParkingSlot(BaseModel):
    parking_lot = models.ForeignKey(ParkingLot, on_delete=models.CASCADE, related_name="slots")
    slot_number = models.CharField(max_length=50, unique=True)
    is_vip = models.BooleanField(default=False) #Ô vip cần book trước
    is_occupied = models.BooleanField(default=False) # Cảm biến báo có xe hay không
    is_look_up = models.BooleanField(default=False)  # Rào chắn đang đóng hay mở
    is_force_released = models.BooleanField(default=False) # Đánh đấu ô vip bị ép hạ rào do bãi xe quá tải

    raw_index = models.PositiveIntegerField(help_text="Hàng thứ mấy")
    column_index = models.PositiveIntegerField(help_text="Cột thứ mấy")
    floor = models.IntegerField(default=1)

    def __str__(self):
        return self.slot_number


class Booking(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="bookings")
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name="bookings")
    slot = models.ForeignKey(ParkingSlot, on_delete=models.CASCADE, related_name="bookings")

    start_time = models.DateTimeField(help_text="Thời gian xe đến")
    end_time = models.DateTimeField(null=True, blank=True, help_text="Thời gian dự kiến rời đi")

    deposit_amount = models.PositiveIntegerField(help_text="Phí đặt chỗ")
    status = models.CharField(max_length=10, choices=BookingStatus.choices, default=BookingStatus.PENDING)

    def __str__(self):
        return f"Booking {self.vehicle.license_plate} - {self.slot.slot_number} - {self.start_time} - {self.end_time}"


class ParkingLog(BaseModel):
    parking_lot = models.ForeignKey(ParkingLot, on_delete=models.PROTECT, related_name="parking_logs")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="parking_logs")
    vehicle_face = models.ForeignKey(VehicleFace, on_delete=models.CASCADE, related_name="parking_logs")
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


# class DynamicPriceRule(BaseModel):
#     """Quy tắc tăng giảm giá theo điều kiện"""
#     name = models.CharField(max_length=50)
#     parking_lot = models.ForeignKey(ParkingLot, on_delete=models.CASCADE, related_name="dynamic_price_rules")
#
#     start_date = models.DateField()
#     end_date = models.DateField()
#
#     # Hệ số nhận
#     multiplier = models.FloatField(default=1)
#     # Độ ưu tiên
#     priority = models.IntegerField(default=0, help_text="Độ ưu tiên nếu có nhiều quy tắc trùng nhau")
