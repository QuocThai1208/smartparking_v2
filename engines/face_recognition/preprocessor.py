"""
    Chuẩn hóa khuôn mặt
"""

import cv2
import numpy as np

class FacePreprocessor:
    def __init__(self, output_size=(112, 112)):
        self.output_size = output_size

    def align_face(self, img, landmarks):
        # Logic xoay ảnh dựa trên vị trí mắt (landmarks)
        # Giúp khuôn mặt luôn thẳng, hỗ trợ Recognizer đọc tốt hơn
        std_points = np.array([
            [30.2946, 51.6963], [65.5318, 51.5014],
            [48.0252, 71.7366], [33.5493, 92.3655],
            [62.7299, 92.2041]
        ], dtype=np.float32)

        # Chỉnh lại tỷ lệ nếu output_size khác 112x112
        if self.output_size != (112, 112):
            std_points[:, 0] *= self.output_size[0] / 112
            std_points[:, 1] *= self.output_size[1] / 112

        # Tính toán ma trận chuyển đổi (Similarity Transformation)
        curr_points = np.array(landmarks, dtype=np.float32)
        tform = cv2.estimateAffinePartial2D(curr_points, std_points)[0]

        if tform is None:
            # Nếu không tính được ma trận, trả về ảnh resize đơn thuần làm phương án dự phòng
            return cv2.resize(img, self.output_size)

        # Thực hiện xoay và cắt ảnh theo ma trận đã tính
        warped = cv2.warpAffine(img, tform, self.output_size, borderValue=0.0)
        return warped

    def process(self, frame, detections):
        """
        :param frame: ảnh từ camera
        :param detections: [{
                            "bbox": tọa độ khuôn mặt,
                            "conf": độ tin cậy,
                            "landmarks": Điểm đặc trưng để xoay ảnh
                            }]
        :return: [{
                    "processed_face": Ảnh đã chuẩn hóa, xoay khuôn mặt
                    "raw_crop": ảnh gốc đã được cẳt
                }]
        """
        processed_faces = []
        for det in detections:
            x1, y1, x2, y2 = det["bbox"]

            # Cắt ảnh thô (Raw Crop) để lưu debug hoặc hiển thị
            raw_face = frame[max(0, y1):y2, max(0, x1):x2]

            if raw_face.size == 0:
                continue

            # Thực hiện Alignment (Xoay khuôn mặt)
            aligned_face = self.align_face(frame, det["landmarks"])

            processed_faces.append({
                "processed_face": aligned_face,
                "raw_crop": raw_face
            })

        return processed_faces
