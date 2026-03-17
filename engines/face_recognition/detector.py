"""
    Phát hiện vùng khuôn mặt
"""

import cv2
from insightface.app import FaceAnalysis

class FaceDetector:
    def __init__(self, conf_threshold=0.8):
        # Khởi tạo mô hình nhận diện khuôn mặt
        self.app = FaceAnalysis(allowed_modules=['detection'])
        self.app.prepare(ctx_id=-1, det_size=(640, 640))
        self.conf_threshold = conf_threshold

    def detector(self, image):
        """
        :param image: ảnh đầu vào từ camera
        :return:
        """
        faces = self.app.get(image)
        detections = []
        for face in faces:
            if face.det_score < self.conf_threshold:
                continue

            bbox = face.bbox.astype(int)
            detections.append({
                'bbox': bbox.tolist(),
                "conf": float(face.det_score),
                "landmarks": face.kps # Điểm đặc trưng để xoay ảnh ở bước sau
            })
        return detections
