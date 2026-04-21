import requests
from django.conf import settings
import os
import traceback

class DetectFaceClient:
    @staticmethod
    def detect_face(face_img):
        url = settings.FACE_SERVICE_URL
        try:
            with open(face_img, 'rb') as file:
                files = {'image_face': (os.path.basename(face_img), file, 'image/jpeg')}

                response = requests.post(url, files=files, timeout=60)
                response.raise_for_status()
                ai_data = response.json()
                embedding = ai_data['data']['embedding']
                processed_face_base64 = ai_data['data']['processed_face']

                if embedding is None or processed_face_base64 is None:
                    raise ValueError("Không nhận diện dược khuôn mặt")
                return embedding, processed_face_base64
        except Exception as e:
            error_msg = f"Lỗi gọi AI: {str(e)} \n {traceback.format_exc()}"
            print(error_msg)
            raise Exception(error_msg)