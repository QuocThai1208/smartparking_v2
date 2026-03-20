from ..models import Wallet, PaymentStatus
from ...users.models import User
from ...finance.models import Payment, PaymentStatus


class PaymentService:
    @staticmethod
    def process_payment(wallet: Wallet, amount: float, description: str) -> tuple[PaymentStatus, str]:
        try:
            wallet.withdraw(amount, description)
        except ValueError as e:
            return PaymentStatus.FAIL, str(e)
        except Exception as e:
            return PaymentStatus.ERROR, str(e)
        return PaymentStatus.SUCCESS, "Thanh toán thành công"

    # HÀM: Tạo mới thanh toán
    @staticmethod
    def create_payment(user: User, fee: int) -> tuple[bool, str]:
        payment = Payment.objects.create(
            user=user,
            amount=fee,
        )
        payment_status, msg = PaymentService.process_payment(user.wallet, fee, description='Thanh toán luợt gửi xe')
        payment.status = payment_status
        payment.save(update_fields=['status'])
        if payment_status in [PaymentStatus.ERROR, PaymentStatus.FAIL]:
            return False, msg
        return True, "Xin mời ra."