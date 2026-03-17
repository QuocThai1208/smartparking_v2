"""
    Dùng YOLOv11 nhận diện vùng biển số
"""
from ultralytics import YOLO

class PlateDetector:
    def __init__(self, model_path, conf_threshold=0.5):
        """
        Khởi tạo detector sử dụng YOLOYv11
        :param model_path: numpy array (opencv frame)
        :return: [{'bbox':[x1,y1,x2,y2],'conf':0.9}]
        """
        # Tự chọn mode tránh lỗi khi chạy trên CPU/CPU
        self.model = YOLO(model_path)
        self.conf_threshold = conf_threshold

    def detect(self, image):
        """
        Phát hiện biển số từ ảnh đầu vào
        :param image: Đường dẫn ảnh hoặc Numpy Array (Open CV)
        :return: List các dictionary chứa các tọa độ bbox và độ tin cậy
        """

        # Kết quả sau khi model nhận diện biển số
        results = self.model(image, conf=self.conf_threshold, iou=0.5, imgsz=360, verbose=False)

        detections = []
        for r in results:
            if r.boxes is None:
                continue
            for box in r.boxes:
                x1, y1, x2, y2 = box.xyxy[0].numpy().astype(int)
                conf = float(box.conf[0])

                detections.append({
                    "bbox": [x1, y1, x2, y2],
                    "conf": conf
                })

        return detections