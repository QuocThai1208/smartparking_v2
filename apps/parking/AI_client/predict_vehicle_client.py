from django.conf import settings
from ..models import FeeType
import requests

class PredictVehicleClient:

    @staticmethod
    def prodict_vehicle(image_front, image_plate):
        """
        :param image_front: ảnh chụp đầu xe
        :param image_plate: ảnh chụp biển số xe
        :return: {
                    'plate': '70G100000',
                    'attributes': {
                                    'color': Red,
                                    'brand': toyota,
                                    'type': Car,
                                  }
                }
        """
        url = settings.PLATE_SERVICE_URL
        # Chuẩn bị file để gửi qua POST request
        files = {
            'image_front': (image_front.name, image_front.read(), image_front.content_type),
            'image_plate': (image_plate.name, image_plate.read(), image_plate.content_type),
        }
        try:
            # Gửi yêu cầu sang AI Service
            response = requests.post(url, files=files, timeout=60)
            response.raise_for_status()
            ai_data = response.json()

            if ai_data['success']:
                return ai_data['data']
        except Exception as e:
            raise ValueError("detail", e)
