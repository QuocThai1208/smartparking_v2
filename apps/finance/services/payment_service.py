from ..models import Wallet, PaymentStatus
from ...users.models import User
from ...finance.models import Payment, PaymentStatus
from decimal import Decimal

class PaymentService:
    @staticmethod
    def process_payment(wallet: Wallet, amount: Decimal, description: str) -> tuple[PaymentStatus, str]:
        try:
            wallet.withdraw(amount, description)
        except ValueError as e:
            return PaymentStatus.FAIL, str(e)
        except Exception as e:
            return PaymentStatus.ERROR, str(e)
        return PaymentStatus.SUCCESS, "Thanh toán thành công"

    # HÀM: Tạo mới thanh toán
    @staticmethod
    def create_payment(user: User, fee: int, description: str) -> tuple[bool, str]:
        fee_decimal = Decimal(str(fee))
        payment = Payment.objects.create(
            user=user,
            amount=fee,
        )
        payment_status, msg = PaymentService.process_payment(user.wallet, fee_decimal, description=description)
        payment.status = payment_status
        payment.save(update_fields=['status'])
        if payment_status in [PaymentStatus.ERROR, PaymentStatus.FAIL]:
            return False, msg
        return True, "Xin mời ra."