from ..models import Vehicle, VehicleFace
from ..AI_client.detect_face_client import DetectFaceClient
from ..utils import save_temp_file


class VehicleFaceService:
    @staticmethod
    def register_new_face(vehicle_id, owner_name, relationship, face_img, is_default):
        try:
            vehicle = Vehicle.objects.get(id=vehicle_id)
        except Vehicle.DoesNotExist:
            raise ValueError("Không tìm thấy thông tin xe.")

        face_img.seek(0)
        face_path = save_temp_file(face_img)
        embedding = DetectFaceClient.detect_face(face_path)
        # 4. Lưu Database
        face_record = VehicleFace.objects.create(
            vehicle=vehicle,
            owner_name=owner_name,
            relationship=relationship,
            face_img=face_img,
            face_vector=embedding,
            is_default=is_default
        )
        return face_record


