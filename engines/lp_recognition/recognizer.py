"""
    Dùng PaddleOCR nhận diện ký tự
"""
import os

# Ép hệ thống tắt OneDNN từ cấp độ biến môi trường
os.environ['FLAGS_allocator_strategy'] = 'naive_best_fit'
os.environ['FLAGS_fraction_of_gpu_memory_to_use'] = '0'
os.environ['PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK'] = 'True'

from paddleocr import PaddleOCR
import re
import cv2


class PlateRecognizer:
    def __init__(self):
        # Khởi tạo PaddleOCR - chỉ cần chạy 1 lần duy nhất
        # use_angle_cls=True giúp nhận diện chữ bị nghiêng
        self.ocr = PaddleOCR(use_angle_cls=False,
                             lang='en',
                             use_gpu=False,
                             enable_mkldnn=True,  # Nếu đã fix được lỗi OneDNN thì bật lại cái này sẽ nhanh hơn 20-30%
                             rec_char_type='en',
                             det_db_thresh=0.3,  # Giảm ngưỡng để detect nhanh hơn
                             det_db_box_thresh=0.5)
        self.plate_pattern = r'^[0-9]{2}[A-Z][0-9]{4,5}$'

    def recognize(self, plate_img):
        """
        :param plate_img: ảnh biển số đã qua sử lý
        :return: Chuỗi ký tự biển số
        """

        """
            result[0]: Danh sách các kết quả cho ảnh thứ nhất
                [[[x1, y1], [x2, y2], [x3, y3], [x4, y4]], # Tọa độ 4 góc của khung bao chữ
                ('30A12345', 0.985)]]                      # (Nội dung chữ, Độ tin cậy)
        """
        if len(plate_img.shape) == 2:
            plate_img = cv2.cvtColor(plate_img, cv2.COLOR_GRAY2BGR)

        result = self.ocr.ocr(plate_img)

        if not result or result[0] is None:
            return ""

        # result[0] chứa danh sách các dòng chữ tìm thấy
        # Với biển số 2 dòng, PaddleOCR sẽ trả về 2 phần tử trong list
        raw_texts = []
        for line in result[0]:
            text = line[1][0]  # Lấy nội dung text
            conf = line[1][1]

            if conf < 0.6:
                continue

            # Loại bỏ các ký tự đặc biệt như dấu gạch ngang, chấm, rác...
            clean = re.sub(r'[^A-Z0-9]', '', text.upper())
            raw_texts.append(clean)

        # Ghép các dòng lại thành 1 chuỗi duy nhất
        full_plate = "".join(raw_texts)

        if re.match(self.plate_pattern, full_plate):
            return full_plate
        return full_plate
