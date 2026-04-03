
from ..task import handle_parking_ai_task
from ..utils import save_temp_file

class ParkingService:
    @staticmethod
    def check_in(parking_lot_id, face_img, image_front, image_plate):
        # 1. Lưu ảnh vào thư mục tạm (hoặc Media)
        face_path = save_temp_file(face_img)
        front_path = save_temp_file(image_front)
        plate_path = save_temp_file(image_plate)

        handle_parking_ai_task.delay('IN', parking_lot_id, face_path, front_path, plate_path)

        # 3. Trả về ngay lập tức
        return True, "Hệ thống đang xử lý AI, vui lòng đợi...", None

    @staticmethod
    def check_out(parking_lot_id, face_img, image_front, image_plate):
        face_path = save_temp_file(face_img)
        front_path = save_temp_file(image_front)
        plate_path = save_temp_file(image_plate)

        handle_parking_ai_task.delay('OUT', parking_lot_id, face_path, front_path, plate_path)

        # 3. Trả về ngay lập tức
        return True, "Hệ thống đang xử lý AI, vui lòng đợi...", None

