import  os

from engines.lp_recognition.detector import PlateDetector
from engines.lp_recognition.preprocessor import PlatePreprocessor
from engines.lp_recognition.recognizer import PlateRecognizer

# Tự động lấy đường dẫn đến file yolo11n_plate.pt
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
WEIGHTS_PATH = os.path.join(CURRENT_DIR, "..", "weights", "yolo11n_plate.pt")

# Khởi tạo sẵn các class (Singleton Pattern)
lp_detector_instance = PlateDetector(WEIGHTS_PATH)
lp_preprocessor_instance = PlatePreprocessor()
lp_recognizer_instance = PlateRecognizer()