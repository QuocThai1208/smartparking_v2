from django.db import models
from ..users.models import User


class PaymentStatus(models.TextChoices):
    PENDING = "PENDING", "Đang xử lý"
    SUCCESS = "SUCCESS", "Thành công"
    FAIL = "FAIL", "Thất bại"
    ERROR = "ERROR", "Lỗi kết nối"


class PaymentType(models.TextChoices):
    BASE = "BASE", "Phí gốc"
    PENALTY = "PENALTY", "Phí phạt đỗ quá hạn"
    TOWING = "TOWING", "Phí cẩu xe"


class TransactionType(models.TextChoices):
    DEPOSIT = "DEPOSIT", "Nạp tiền"
    WITHDRAW = "WITHDRAW", "Rút tiền",
    PAYMENT = "PAYMENT", "Thanh toán",
    REFUND = "REFUND", "Hoàn tiền"


class BaseModel(models.Model):
    active = models.BooleanField(default=True)
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ['-id']


class Payment(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="payments")
    amount = models.PositiveIntegerField(help_text="Số tiền giao dịch (VNĐ)")
    status = models.CharField(max_length=10, choices=PaymentStatus.choices, default=PaymentStatus.PENDING)
    type = models.CharField(max_length=10, choices=PaymentType.choices, default=PaymentType.BASE)

    def __str__(self):
        return f"{self.id} - {self.amount}đ ({self.status})"


class Wallet(BaseModel):
    user = models.OneToOneField(User, on_delete=models.PROTECT, related_name="wallet")
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)

    def __str__(self):
        return f"Ví của {self.user.full_name} - {self.balance:.2f}vnđ"

    def can_afford(self, amount):
        return self.balance >= amount

    def deposit(self, amount, description=''):
        if amount <= 0:
            raise ValueError("Số tiền nạp phải lớn hơn 0.")

        self.balance += amount
        self.save()
        WalletTransaction.objects.create(
            wallet=self,
            amount=amount,
            transaction_type=TransactionType.DEPOSIT,
            description=description
        )

    def withdraw(self, amount, description=''):
        if not self.active:
            raise ValueError("Ví đã bị khóa.")

        if amount <= 0:
            raise ValueError("Số tiền rút phải lớn hơn 0.")
        if self.balance < amount:
            raise ValueError("Số dư không đủ.")

        self.balance -= amount
        self.save()
        WalletTransaction.objects.create(
            wallet=self,
            amount=amount,
            transaction_type=TransactionType.WITHDRAW,
            description=description
        )


class WalletTransaction(BaseModel):
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name="transaction")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    transaction_type = models.CharField(max_length=10, choices=TransactionType.choices)
    description = models.TextField(blank=True)

    def __str__(self):
        return f"{self.transaction_type} {self.amount}vnđ - {self.created_date.strftime('%d-%m-%Y %H:%M:%S')}"