from ..models import Vehicle, VehicleFace
import requests
from django.conf import settings

class DetectFaceClient:
    @staticmethod
    def detect_face(face_img):
        url = settings.FACE_SERVICE_URL
        files = {'image_face': (face_img.name, face_img.read(), face_img.content_type)}
        try:
            response = requests.post(url, files=files, timeout=60)
            response.raise_for_status()
            ai_data = response.json()
            embedding = ai_data['data']['embedding']

            if embedding is None:
                raise ValueError("Không nhận diện dược khuôn mặt")
            return embedding
        except Exception as e:
            raise ValueError("detail", e)