from ..models import Vehicle, VehicleFace
import numpy as np
import cv2
from engines.face_recognition import (
    face_detector_instance,
    face_preprocessor_instance,
    face_recognizer_instance
)

class VehicleFaceService:
    @staticmethod
    def register_new_face(vehicle_id, owner_name, face_img, is_default):
        try:
            vehicle = Vehicle.objects.get(id=vehicle_id)
        except Vehicle.DoesNotExist:
            raise ValueError("Không tìm thấy thông tin xe.")

        # Đọc ảnh từ bộ nhớ (InMemoryUploadedFile)
        file_bytes = np.frombuffer(face_img.read(), np.uint8)
        image = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)

        # Bước 1: Detect
        detections = face_detector_instance.detect(image)
        if not detections:
            raise ValueError("Không phát hiện được khuôn mặt trong ảnh.")

        # Bước 2: Preprocess
        processed_list = face_preprocessor_instance.process(image, detections)
        if not processed_list:
            raise ValueError("Lỗi trong quá trình chuẩn hóa khuôn mặt.")

        # Bước 3: Recognize (Lấy vector)
        aligned_face = processed_list[0]['processed_face']
        face_vector = face_recognizer_instance.extract_embedding(aligned_face)

        # 4. Lưu Database
        face_record = VehicleFace.objects.create(
            vehicle=vehicle,
            owner_name=owner_name,
            face_img=face_img,
            face_vector=face_vector,
            is_default=is_default
        )

        return face_record