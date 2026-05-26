from datetime import timedelta

from django.utils import timezone
from django.db import transaction

from apps.finance.models import Payment, PaymentType, PaymentStatus
from apps.finance.services.payment_service import PaymentService
from apps.parking.models import MonthlySubscription, MonthlyStatus, NotificationTypes
from apps.parking.services.notification_services import create_and_send_notification


def call_payment(user, amount, vehicle):
    payment = Payment.objects.create(
        user=user,
        amount=amount,
        type=PaymentType.BASE
    )
    payment_status, msg = PaymentService.process_payment(user.wallet, amount, description="Thanh toán vé tháng")
    payment.status = payment_status
    payment.save(update_fields=['status'])
    if payment_status in [PaymentStatus.ERROR, PaymentStatus.FAIL]:
        return False, msg

    create_and_send_notification(
        user.id,
        f"Thanh toán phí vé tháng cho phương tiện {vehicle.license_plate}.",
        f"Thanh toán vé tháng - {amount} đ",
        NotificationTypes.FINANCE)
    return True, msg


def create_monthly_subscription(user, vehicle, package):
    subscription = None
    is_success = False

    with transaction.atomic():
        start_date = timezone.now().date()
        end_date = start_date + timedelta(days=30)
        price = package.price

        subscription = MonthlySubscription.objects.create(
            user=user,
            vehicle=vehicle,
            package=package,
            start_date=start_date,
            end_date=end_date,
            price=price,
            status=MonthlyStatus.PENDING
        )

        is_success, msg = call_payment(user, price, vehicle)

        if is_success:
            subscription.status = MonthlyStatus.ACTIVE
        else:
            subscription.status = MonthlyStatus.FAILED
        subscription.save(update_fields=['status'])
    return subscription, is_success, msg
