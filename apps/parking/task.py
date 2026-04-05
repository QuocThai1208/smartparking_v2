from asgiref.sync import async_to_sync
from celery import shared_task
from channels.layers import get_channel_layer
from django.db import transaction
import numpy as np
from apps.parking.AI_client.detect_face_client import DetectFaceClient
from apps.parking.AI_client.predict_vehicle_client import PredictVehicleClient
from .models import ParkingLog, Vehicle, ParkingStatus, Booking, BookingStatus
from .services.parking_log_service import ParkingLogService, ParkingLogStatsService
from ..finance.services.payment_service import PaymentService
from django.conf import settings
from core.celery import app
from django.utils import timezone

@shared_task
def handle_parking_ai_task(action_type, parking_lot_id, face_img_path, img_front_path, img_plate_path):
    """
    action_type: 'IN' hoặc 'OUT'
    Truyền đường dẫn ảnh thay vì object ảnh để Celery dễ xử lý (serialize)
    """
    channel_layer = get_channel_layer()
    print(f"--- Đang bắt đầu Task {action_type} ---")
    try:
        # Gọi FastAPI
        print(f"Gọi FastAPI tại: {settings.PLATE_SERVICE_URL}")
        print(f"Gọi FastAPI tại: {settings.FACE_SERVICE_URL}")
        res = PredictVehicleClient.prodict_vehicle(img_front_path, img_plate_path)
        embedding = DetectFaceClient.detect_face(face_img_path)
        if action_type == 'IN':
            success, msg, result = process_logic_in(parking_lot_id, res, embedding)
        elif action_type == 'OUT':
            success, msg, result = process_logic_out(parking_lot_id, res, embedding)
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
            return False, "Không tìm thấy phương tiện khớp với biển số", None

        if vehicle.color != color or vehicle.brand != brand or vehicle.type != type:
            return False, "Phương tiện không hợp lệ", None

        all_faces = vehicle.faces.all()
        if not all_faces.exists():
            return False, "Phương tiện này chưa đăng ký khuôn mặt chủ xe", None

        best_face = facial_verification_check_in(all_faces, embedding)
        if best_face is None:
            return False, "Xác minh khuôn mặt thất bại", None
        success, msg = ParkingLogService.create_parking_log(parking_lot_id, vehicle, vehicle.type, best_face)
        # gửi dữ liệu xuống client
        if success:
            channel_layer = get_channel_layer()
            new_data = {
                "type": "parking_current_stats_update",
                "result": ParkingLogStatsService.get_parking_current_stats()
            }

            async_to_sync(channel_layer.group_send)(
                "analytics_group",
                {
                    "type": "send_update",
                    "data": new_data
                }
            )

        return success, msg, {
            'plate': plate_text,
            'type': type,
            'brand': brand,
            'color': color,
        }
    except Exception as e:
        print(f"Lỗi {e}")


def process_logic_out(parking_lot_id, res, embedding):
    plate_text = res['plate']
    type = res['attributes']['type']
    brand = res['attributes']['brand']
    color = res['attributes']['color']

    vehicle = Vehicle.objects.select_related("user").prefetch_related("parking_logs").filter(
        license_plate=plate_text,
        is_approved=True
    ).first()

    temp_log = ParkingLog.objects.filter(vehicle=vehicle, status=ParkingStatus.IN).select_related(
        'vehicle_face').last()

    if vehicle is None:
        return False, "Không tìm thấy phương tiện khớp với biển số", None

    if vehicle.color != color or vehicle.brand != brand or vehicle.type != type:
        return False, "Phương tiện không hợp lệ", None

    result_face_verification = face_verification_check_out(temp_log.vehicle_face, embedding)
    if not result_face_verification:
        return False, "Xác minh khuôn mặt thất bại", None

    print("tìm thấy phương tiện.")

    with transaction.atomic():
        ok, log = ParkingLogService.update_parking(parking_lot_id, vehicle)
        try:
            if log.final_amount_to_pay > 0:
                ok, msg = PaymentService.create_payment(vehicle.user, log.final_amount_to_pay, 'Thanh toán luợt gửi xe')
            print(f"ok: {ok}, msg: {msg}")
            if not ok:
                raise ValueError(msg)
            log.save(
                update_fields=['check_out', 'duration_minutes', 'status', 'fee', 'final_amount_to_pay']
            )
        except Exception as e:
            return ok, "Có lỗi " + str(e), None

    # gửi dữ liệu xuống client
    if ok:
        channel_layer = get_channel_layer()
        new_data = {
            "type": "parking_current_stats_update",
            "result": ParkingLogStatsService.get_parking_current_stats()
        }

        async_to_sync(channel_layer.group_send)(
            "analytics_group",
            {
                "type": "send_update",
                "data": new_data
            }
        )

    return ok, msg, {
        'plate': plate_text,
        'type': type,
        'brand': brand,
        'color': color,
    }


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


def update_status_booking(booking: Booking, status: BookingStatus ):
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
    except Booking.DoesNotExist:
        pass
