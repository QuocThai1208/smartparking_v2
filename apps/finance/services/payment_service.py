from ..models import Wallet, PaymentStatus


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