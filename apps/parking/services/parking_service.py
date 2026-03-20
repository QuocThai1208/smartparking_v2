from ..AI_client.predict_vehicle_client import PredictVehicleClient
from ..AI_client.detect_face_client import DetectFaceClient
from ..models import Vehicle, ParkingStatus, ParkingLog
from ..services.parking_log_service import ParkingLogService
import numpy as np
from django.db import transaction

from ...finance.services.payment_service import PaymentService


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

def face_verification_check_out(face, embedding):
    threshold = 0.5
    dist = calculate_distance(embedding, face.face_vector)
    if dist <= threshold:
        return True
    return False


class ParkingService:
    @staticmethod
    def check_in(face_img, image_front, image_plate):
        res = PredictVehicleClient.prodict_vehicle(image_front, image_plate)
        embedding = DetectFaceClient.detect_face(face_img)

        plate_text = res['plate']
        type = res['attributes']['type']
        brand = res['attributes']['brand']
        color = res['attributes']['color']

        vehicle = Vehicle.objects.prefetch_related("faces").filter(
            license_plate=plate_text,
            is_approved=True
        ).first()

        if vehicle is None:
            return False, "Không tìm thấy phương tiện khớp với biển số"

        if vehicle.color != color or vehicle.brand != brand or vehicle.type != type:
            return False, "Phương tiện không hợp lệ"

        all_faces = vehicle.faces.all()
        if not all_faces.exists():
            return False, "Phương tiện này chưa đăng ký khuôn mặt chủ xe"

        best_face = facial_verification_check_in(all_faces, embedding)
        if best_face is None:
            return False, "Xác minh khuôn mặt thất bại"

        success, msg = ParkingLogService.create_parking_log(vehicle, vehicle.type, best_face)
        return success, msg

    @staticmethod
    def check_out(face_img, image_front, image_plate):
        res = PredictVehicleClient.prodict_vehicle(image_front, image_plate)
        embedding = DetectFaceClient.detect_face(face_img)
        plate_text = res['plate']
        type = res['attributes']['type']
        brand = res['attributes']['brand']
        color = res['attributes']['color']

        vehicle = Vehicle.objects.select_related("user").prefetch_related("parking_logs").filter(
            license_plate=plate_text,
            is_approved=True
        ).first()

        temp_log = ParkingLog.objects.filter(vehicle=vehicle, status=ParkingStatus.IN).select_related('vehicle_face').last()

        if vehicle is None:
            return False, "Không tìm thấy phương tiện khớp với biển số"

        if vehicle.color != color or vehicle.brand != brand or vehicle.type != type:
            return False, "Phương tiện không hợp lệ"

        result_face_verification = face_verification_check_out(temp_log.vehicle_face, embedding)
        if not result_face_verification:
            return False, "Xác minh khuôn mặt thất bại"

        with transaction.atomic():
            ok, log = ParkingLogService.update_parking(vehicle)
            try:
                ok, msg = PaymentService.create_payment(vehicle.user, log.fee)
                if not ok:
                    raise ValueError(msg)
                log.save(
                    update_fields=['check_out', 'duration_minutes', 'status', 'fee']
                )
            except Exception as e:
                return ok, "Có lỗi " + str(e)
        return ok, msg


