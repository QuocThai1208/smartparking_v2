from datetime import timedelta

from asgiref.sync import async_to_sync
from celery import shared_task
from channels.layers import get_channel_layer
from django.db import transaction
import numpy as np
from apps.parking.AI_client.detect_face_client import DetectFaceClient
from apps.parking.AI_client.predict_vehicle_client import PredictVehicleClient
from .models import ParkingLog, Vehicle, ParkingStatus, Booking, BookingStatus, ParkingSlot, NotificationTypes, \
    ParkingLot
from .services.notification_services import create_and_send_notification
from .services.parking_log_service import ParkingLogService, ParkingLogStatsService
from ..finance.models import PaymentType
from ..finance.services.payment_service import PaymentService
from django.conf import settings
from core.celery import app
from django.utils import timezone


@shared_task
def handle_parking_ai_task(action_type, parking_lot_id, face_img_path, img_front_path, img_plate_path):
    channel_layer = get_channel_layer()
    print(f"--- Đang bắt đầu Task {action_type} ---")
    try:
        # Gọi FastAPI
        print(f"Gọi FastAPI tại: {settings.PLATE_SERVICE_URL}")
        print(f"Gọi FastAPI tại: {settings.FACE_SERVICE_URL}")
        res, vehicle_detect_base64 = PredictVehicleClient.prodict_vehicle(img_front_path, img_plate_path)
        embedding, processed_face_base64 = DetectFaceClient.detect_face(face_img_path)
        if action_type == 'IN':
            success, msg, result = process_logic_in(parking_lot_id, res, embedding)
        elif action_type == 'OUT':
            success, msg, result = process_logic_out(parking_lot_id, res, embedding)

        print(f"result {result} msg: {msg}, success: {success}")

        result = result or {}
        result['plate_detect'] = vehicle_detect_base64.get('processed_plate')
        result['vehicle_detect'] = vehicle_detect_base64.get('vehicle_crop')
        result['face_detect'] = processed_face_base64

        async_to_sync(channel_layer.group_send)(
            "analytics_group",
            {
                "type": "send_update",
                "data": {
                    "type": "ai_process_result",
                    "status": "success" if success else "error",
                    "message": msg,
                    "result": result
                }
            }
        )
    except Exception as e:
        # Gửi thông báo lỗi nếu AI sập
        async_to_sync(channel_layer.group_send)(
            "analytics_group",
            {
                "type": "send_update",
                "data": {
                    "type": "error",
                    "message": str(e)
                }
            }
        )


def process_logic_in(parking_lot_id, res, embedding):
    try:
        plate_text = res['plate']
        type = res['attributes']['type']
        brand = res['attributes']['brand']
        color = res['attributes']['color']

        vehicle = Vehicle.objects.prefetch_related("faces").filter(
            license_plate=plate_text,
            is_approved=True
        ).first()

        if vehicle is None:
            print("Không tìm thấy phương tiện khớp với biển số")
            return False, "Không tìm thấy phương tiện khớp với biển số", None

        if vehicle.color != color or vehicle.brand != brand or vehicle.type != type:
            return False, "Phương tiện không hợp lệ", None

        all_faces = vehicle.faces.all()
        if not all_faces.exists():
            print("Phương tiện này chưa đăng ký khuôn mặt chủ xe")
            return False, "Phương tiện này chưa đăng ký khuôn mặt chủ xe", None

        best_face = facial_verification_check_in(all_faces, embedding)
        if best_face is None:
            print("Xác minh khuôn mặt thất bại")
            return False, "Xác minh khuôn mặt thất bại", None

        booking = Booking.objects.filter(
            vehicle=vehicle,
            lot_id=parking_lot_id,
            status=BookingStatus.ACTIVE,
        ).first()

        with transaction.atomic():
            if booking:
                earliest_check_in_time = booking.start_time - timedelta(minutes=10)
                if timezone.now() < earliest_check_in_time:
                    diff = earliest_check_in_time - timezone.now()
                    minutes_to_wait = int(diff.total_seconds() // 60)
                    print(f"Bạn đến quá sớm. Vui lòng quay lại sau {minutes_to_wait} phút nữa.")
                    return False, f"Bạn đến quá sớm. Vui lòng quay lại sau {minutes_to_wait} phút nữa.", None

                # Tìm slot trống cho loại xe này (ưu tiên id thấp nhất)
                assigned_slot = ParkingSlot.objects.filter(
                    parking_lot_id=parking_lot_id,
                    vehicle_type=vehicle.type,
                    is_occupied=False
                ).order_by('id').first()

                if not assigned_slot:
                    print("Bãi xe hiện tại đã thực sự hết chỗ trống")
                    return False, "Bãi xe hiện tại đã thực sự hết chỗ trống", None

                booking.slot = assigned_slot
                booking.task_id = None
                booking.status = BookingStatus.PARKING
                booking.save()

            success, msg = ParkingLogService.create_parking_log(
                parking_lot_id,
                vehicle,
                vehicle.type,
                best_face,
                booking=booking)
        # gửi dữ liệu xuống client
        if success:
            channel_layer = get_channel_layer()
            new_data = {
                "type": "parking_current_stats_update",
                "result": ParkingLogStatsService.get_parking_current_stats(parking_lot_id, type)
            }

            async_to_sync(channel_layer.group_send)(
                "analytics_group",
                {
                    "type": "send_update",
                    "data": new_data
                }
            )
            lot = ParkingLot.objects.filter(id=parking_lot_id).first()
            create_and_send_notification(
                vehicle.user.id,
                "Đỗ xe thành công.",
                f"Bạn qua cổng thành công tại bãi xe {lot.name}",
                NotificationTypes.PARKING)

        return success, msg, {
            'plate': plate_text,
            'type': type,
            'brand': brand,
            'color': color,
        }
    except Exception as e:
        print(f"Lỗi {e}")


def process_logic_out(parking_lot_id, res, embedding):
    try:
        plate_text = res['plate']
        type = res['attributes']['type']
        brand = res['attributes']['brand']
        color = res['attributes']['color']

        vehicle = Vehicle.objects.select_related("user").prefetch_related("parking_logs").filter(
            license_plate=plate_text,
            is_approved=True
        ).first()

        print("Kiểm tra temp_log.")

        temp_log = ParkingLog.objects.filter(parking_lot_id=parking_lot_id, vehicle=vehicle,
                                             status=ParkingStatus.IN).select_related('vehicle_face').last()

        print("Kiểm tra phương tiện.")
        if vehicle is None:
            return False, "Không tìm thấy phương tiện khớp với biển số", None

        print("Kiểm tra thuộc tính.")
        if vehicle.color != color or vehicle.brand != brand or vehicle.type != type:
            return False, "Phương tiện không hợp lệ", None

        print("Kiểm tra log.")
        if temp_log is None:
            return False, "Không tìm thấy phương tiện trông bãi", None

        result_face_verification = face_verification_check_out(temp_log.vehicle_face, embedding)
        if not result_face_verification:
            return False, "Xác minh khuôn mặt thất bại", None

        print("tìm thấy phương tiện.")
        ok = False
        msg = "Xin mời ra"
        with transaction.atomic():
            ok, log, fees_detail = ParkingLogService.update_parking(parking_lot_id, vehicle)
            print("Cập nhật log thành công.")
            for item in fees_detail:
                if item['fee'] > 0:
                    # Tạo payment riêng cho từng loại phí
                    pay_ok, msg = PaymentService.create_payment(
                        user=vehicle.user,
                        fee=item['fee'],
                        description=f"{item['description']} cho xe {vehicle.name}-{vehicle.license_plate}",
                        type=item['type']
                    )
                    if not pay_ok:
                        return pay_ok, msg, {
                            'plate': plate_text,
                            'type': type,
                            'brand': brand,
                            'color': color,
                        }
            print("Thanh toán thành công.")
            log.save(
                update_fields=['check_out', 'duration_minutes', 'status', 'fee', 'final_amount_to_pay']
            )

        # gửi dữ liệu xuống client
        if ok:
            channel_layer = get_channel_layer()
            new_data = {
                "type": "parking_current_stats_update",
                "result": ParkingLogStatsService.get_parking_current_stats(parking_lot_id, type)
            }

            async_to_sync(channel_layer.group_send)(
                "analytics_group",
                {
                    "type": "send_update",
                    "data": new_data
                }
            )

            lot = ParkingLot.objects.filter(id=parking_lot_id).first()
            create_and_send_notification(
                vehicle.user.id,
                "Lấy xe thành công.",
                f"Bạn qua cổng thành công tại bãi xe {lot.name}",
                NotificationTypes.PARKING)

        return ok, msg, {
            'plate': plate_text,
            'type': type,
            'brand': brand,
            'color': color,
        }

    except Exception as e:
        print(f"Có lỗi {str(e)}")


def face_verification_check_out(face, embedding):
    threshold = 0.5
    dist = calculate_distance(embedding, face.face_vector)
    if dist <= threshold:
        return True
    return False


def calculate_distance(embedding1, embedding2):
    # Chuyển về numpy array nếu đang là list
    img1_representation = np.array(embedding1)
    img2_representation = np.array(embedding2)

    # Tính Euclidean Distance (Khoảng cách càng nhỏ càng giống nhau)
    distance = np.linalg.norm(img1_representation - img2_representation)
    return distance


def facial_verification_check_in(all_faces, embedding):
    best_distance = float('inf')
    best_face = None
    threshold = 0.5

    for face_obj in all_faces:
        dist = calculate_distance(embedding, face_obj.face_vector)
        if dist < best_distance:
            best_distance = dist
            best_face = face_obj

    if best_distance <= threshold and best_face:
        return best_face
    return None


def update_status_booking(booking: Booking, status: BookingStatus):
    booking.status = status
    booking.save()


# Hủy booking nếu khách kh đến đúng hẹn
@shared_task
def check_booking_expired(booking_id):
    try:
        booking = Booking.objects.get(id=booking_id)
        if booking.status == BookingStatus.ACTIVE:
            booking.status = BookingStatus.EXPIRED
            booking.save()
            print(f"Booking {booking_id} đã hết hạn.")
            create_and_send_notification(
                booking.user.id,
                "Hết hạn đặt chỗ.",
                f"Lịch đặt chỗ cho phương tiện {booking.vehicle.name}-{booking.vehicle.license_plate} tại {booking.lot.name} đã hết hạn",
                NotificationTypes.PARKING)
    except Booking.DoesNotExist:
        print(f"Không tìm thấy Booking ID {booking_id} để hủy.")


# Gửi thông báo nếu xe đỗ quá thời gian book
@shared_task
def notify_overtime_booking(booking_id):
    try:
        booking = Booking.objects.select_related('lot', 'vehicle', 'user').get(id=booking_id)

        # thông báo nếu xe vẫn đang đỗ (PARKING)
        if booking.status == BookingStatus.PARKING:
            create_and_send_notification(
                booking.lot.owner.id,
                "Xe đỗ quá hạn.",
                f"Phương tiện {booking.vehicle.name}-{booking.vehicle.license_plate} tại {booking.lot.name} đã đỗ quá hạn đối với thời gian đặt chỗ booking.end_time.strftime('%H:%M %d/%m/%Y').",
                NotificationTypes.PARKING)
            print(f"Đã gửi cảnh báo quá hạn cho Booking {booking_id}")

    except Booking.DoesNotExist:
        print(f"Không tìm thấy Booking ID {booking_id} để gửi cảnh báo.")
