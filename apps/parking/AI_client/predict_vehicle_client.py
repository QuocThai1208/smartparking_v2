import os.path
import traceback

from django.conf import settings
import requests

class PredictVehicleClient:

    @staticmethod
    def prodict_vehicle(image_front_path, image_plate_path):
        """
        :param image_front_path: đường dẫn ảnh chụp đầu xe
        :param image_plate_path: đường dẫn ảnh chụp biển số xe
        :return: {
                    'plate': '70G100000',
                    'attributes': {
                                    'color': Red,
                                    'brand': toyota,
                                    'type': Car,
                                    'vehicle_crop': File
                                  }
                    'processed_plate': File
                }
        """
        url = settings.PLATE_SERVICE_URL

        try:
            with open(image_front_path, 'rb') as f_front, open(image_plate_path, 'rb') as f_plate:
                # Chuẩn bị file để gửi qua POST request
                files = {
                    'image_front': (os.path.basename(image_front_path), f_front, 'image/jpeg'),
                    'image_plate': (os.path.basename(image_plate_path), f_plate, 'image/jpeg'),
                }

                # Gửi yêu cầu sang AI Service
                response = requests.post(url, files=files, timeout=60)
                response.raise_for_status()
                ai_data = response.json()

                if ai_data['success']:
                    return ai_data['data'], ai_data['file']
            raise ValueError("AI Service return success: False")
        except Exception as e:
            error_msg = f"Lỗi gọi AI: {str(e)} \n {traceback.format_exc()}"
            print(error_msg)  # Để nó hiện lên terminal/log của container
            raise Exception(error_msg)  # Ném lỗi thực sự để Celery biết mà báo FAILED
