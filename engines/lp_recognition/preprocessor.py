"""
    Thực hiện nhiệm vụ cắt ảnh biển số, cải thiện chất lượng ảnh
"""
import cv2
import numpy as np


class PlatePreprocessor:
    def __init__(self, output_size=(320, 120)):
        # Kích thước chuẩn để đưa vào nhận diện ký tự
        self.output_size = output_size

    def resize_with_padding(self, img):

        target_w, target_h = self.output_size
        h, w = img.shape[:2]

        scale = min(target_w / w, target_h / h)

        new_w = int(w * scale)
        new_h = int(h * scale)

        resized = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4)

        canvas = np.zeros((target_h, target_w), dtype=np.uint8)

        x_offset = (target_w - new_w) // 2
        y_offset = (target_h - new_h) // 2

        canvas[y_offset:y_offset + new_h, x_offset:x_offset + new_w] = resized

        return canvas

    def process(self, frame, detections):
        """
        :param frame: Ảnh gốc từ camera
        :param detections: danh sách tọa độ từ detector [{'bbox': [x1,y1,x2,y2], 'conf': 0.9}]
        :return: [{"processed_plate": final_plate, "raw_crop": plate_img, "bbox": [x1, y1, x2, y2]}]
        """
        processed_plates = []
        h_orig, w_orig = frame.shape[:2]

        for detection in detections:
            x1, y1, x2, y2 = detection["bbox"]

            margin_w = int((x2 - x1) * 0.10)
            margin_h = int((y2 - y1) * 0.10)

            # Tính lại margin kích thước sau khi thêm margin kh được vượt quá kích thước ảnh
            crop_x1 = max(0, x1 - margin_w)
            crop_y1 = max(0, y1 - margin_h)
            crop_x2 = min(w_orig, x2 + margin_w)
            crop_y2 = min(h_orig, y2 + margin_h)

            # cắt vùng biển số
            plate_img = frame[crop_y1:crop_y2, crop_x1:crop_x2]

            if plate_img.size == 0:
                continue

            # *** Tăng chất lượng ảnh
            # Chuyển xám
            gray = cv2.cvtColor(plate_img, cv2.COLOR_BGR2GRAY)

            # Sử dụng CLAHE để cân bằng độ sáng (giúp biển số bị chói đèn pha vẫn đọc được)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(gray)

            # Loại bỏ nhiễu (Dùng GaussianBlur)
            # Điều này giúp làm mịn các hạt nhiễu li ti
            blurred = cv2.GaussianBlur(enhanced, (3, 3), 0)

            # Resize về kích thước chuẩn
            final_plate = self.resize_with_padding(blurred)
            processed_plates.append({
                "processed_plate": final_plate,
                "raw_crop": plate_img,
                "bbox": [x1, y1, x2, y2]
            })

        return processed_plates
