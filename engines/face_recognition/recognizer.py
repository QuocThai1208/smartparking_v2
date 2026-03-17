"""
    Nhận diện danh tính
"""

from deepface import DeepFace


class FaceRecognizer:
    def __init__(self, model_name="ArcFace"):
        self.model_name = model_name

    def extract_embedding(self, aligned_face):
        """
        :param aligned_face: Ảnh đã được xoay thẳng từ Preprocessor
        :return: vector 512 chiều đặc trưng của khuôn mặt
        """

        embedding_objs = DeepFace.represent(
            img_path=aligned_face,
            model_name=self.model_name,
            enforce_detection=False,  # tắc đi vì đã detect ở bước trước
            detector_backend='skip'  # Bỏ qua bước detect nội bộ để tăng tốc
        )
        return embedding_objs[0]['embedding']