from django.db.models import Q
from django.utils import timezone
from ..models import PublicHoliday, ParkingLotPolicy, PriceStrategyTemplate


class PriceEngine:
    @staticmethod
    def calculate_final_price(parking_lot_id, base_price, target_time):
        """
        Tính toán giá dựa trên các điều kiện thời gian và mật độ.
        """
        multipliers = [(1.0, "Giá cơ bản")]  # Mặc định là hệ số 1.0 (không tăng giá)

        # Kiểm tra bãi xe này có áp dụng thu thêm phí ngày lễ
        is_holiday = PublicHoliday.objects.filter(date=target_time.date()).first()
        if is_holiday:
            policy = ParkingLotPolicy.objects.filter(
                parking_lot_id=parking_lot_id,
                strategy__code='HOLIDAY',
                holiday=is_holiday,
                active=True
            ).filter(
                Q(holiday=is_holiday) | Q(holiday__isnull=True)
            ).order_by('-holiday').first()
            if policy:
                multipliers.append((policy.multiplier, f"Ngày lễ {is_holiday.name} (x{policy.multiplier})"))

        # Kiểm tra bãi xe này có áp dụng thu thêm phí cuối tuần (Thứ 7 = 5, Chủ nhật = 6)
        if target_time.weekday() in [5, 6]:
            policy = ParkingLotPolicy.objects.filter(
                parking_lot_id=parking_lot_id,
                strategy__code='WEEKEND',
                holiday__isnull=True,
                active=True
            ).first()
            if policy:
                day_name = "Thứ 7" if target_time.weekday() == 5 else "Chủ nhật"
                multipliers.append((policy.multiplier, f"Cuối tuần {day_name} (x{policy.multiplier})"))

        # Lấy hệ số cao nhất
        final_multiplier, best_reason  = max(multipliers, key=lambda x: x[0]) # hệ số cao nhất
        total_fee = base_price * final_multiplier # tổng phí đỗ xe
        surcharge = total_fee - base_price # phí thu thêm

        print(f"base_price: {base_price}")
        print(f"final_multiplier: {final_multiplier}")
        print(f"surcharge: {surcharge}")
        print(f"total_fee: {total_fee}")

        return {
            "base_price": base_price,
            "surcharge": surcharge,
            "total_fee": total_fee,
            "note": best_reason if final_multiplier > 1.0 else "Giá tiêu chuẩn",
        }