import math
from ..models import Vehicle, ParkingLog, ParkingStatus, FeeRule, FeeType
from django.db import transaction
from django.utils import timezone
from apps.finance.services.payment_service import PaymentService
from ...finance.models import Payment, PaymentStatus
from ...users.models import User, UserRole

class HandleParkingService:
    # HÀM: tính phí giữ xe
    @staticmethod
    def calculate_fee(minutes: int, fee_rule: FeeRule) -> int:
        if fee_rule.fee_type in [FeeType.MOTORCYCLE, FeeType.CAR]:
            day = max(1, math.ceil(minutes / (24 * 60)))
            return day * fee_rule.amount

        raise ValueError(f"Unsupport fee_type: {fee_rule.fee_type}")

    # HÀM: Cập nhật nhật kí gửi xe
    def update_parking(v: Vehicle) -> tuple[bool, ParkingLog or str]:
        try:
            log = (
                ParkingLog.objects
                .select_for_update()  # khóa bảng ghi cho đến khi hoàn tất
                .get(user=v.user,
                     vehicle=v,
                     status=ParkingStatus.IN)
            )
        except  ParkingLog.DoesNotExist:
            return False, "Không tìm thấy xe lượt vào bãi"

        now = timezone.now()
        log.check_out = now
        duration = int((log.check_out - log.check_in).total_seconds() // 60)
        log.duration_minutes = duration
        log.status = ParkingStatus.OUT
        log.fee = HandleParkingService.calculate_fee(duration, log.fee_rule)
        return True, log

    # HÀM: Tạo mới nhật kí gửi xe
    @staticmethod
    def create_parking(v: Vehicle, fee_type: FeeType) -> tuple[bool, str]:
        exist_p = ParkingLog.objects.filter(user=v.user, vehicle=v, status=ParkingStatus.IN).first()
        if exist_p:
            return False, 'Phương tiện này đang có trong bãi'
        p = ParkingLog.objects.create(
            user=v.user,
            vehicle=v,
            fee_rule=FeeRule.objects.get(fee_type=fee_type),
            status=ParkingStatus.IN
        )
        if p:
            return True, "Xin mời vào."
        return False, "Không hợp lệ."

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

    @staticmethod
    def proces(plate_text: str, direction: ParkingStatus = "IN") -> tuple[bool, str]:
        vehicle = Vehicle.objects.select_related("user").filter(
            license_plate=plate_text,
            is_approved=True
        ).first()

        if vehicle is None:
            return False, "Không tìm thấy phương tiện khớp với biển số"

        if direction == 'OUT':
            with transaction.atomic():
                ok, log = HandleParkingService.update_parking(vehicle)
                if not ok:
                    return ok, log
                try:
                    ok, msg = HandleParkingService.create_payment(vehicle.user, log.fee)
                    if not ok:
                        raise ValueError(msg)
                    log.save(
                        update_fields=['check_out', 'duration_minutes', 'status', 'fee']
                    )
                except Exception as e:
                    return ok, "Có lỗi " + str(e)
            return ok, msg

        ok, msg = HandleParkingService.create_parking(vehicle, vehicle.vehicle_type)
        return ok, msg

    @staticmethod
    def get_total_customer():
        total_customer = User.objects.filter(user_role=UserRole.CUSTOMER).count()
        return {"totalCustomer": total_customer}