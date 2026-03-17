import cv2
import os
import time
from engines.lp_recognition.detector import PlateDetector
from engines.lp_recognition.preprocessor import PlatePreprocessor
from engines.lp_recognition.recognizer import PlateRecognizer


def test_system():
    # --- ĐO THỜI GIAN KHỞI TẠO ---
    start_init = time.time()

    model_path = 'engines/weights/yolo11n_plate.pt'
    image_path = 'media/test/test_7.jpg'

    if not os.path.exists(image_path):
        print(f"❌ Cần bỏ ảnh {image_path} vào thư mục gốc để test!")
        return

    print("🚀 Đang khởi tạo hệ thống từ engines...")

    detector = PlateDetector(model_path)
    preprocessor = PlatePreprocessor()
    recognizer = PlateRecognizer()

    init_duration_ms = (time.time() - start_init) * 1000
    print(f"⏱️ Thời gian khởi tạo hệ thống: {init_duration_ms:.2f} ms")
    print("-" * 40)

    frame = cv2.imread(image_path)
    cv2.imshow("1. Anh Goc", cv2.resize(frame, (800, 600)))  # Show ảnh gốc

    # --- TỔNG THỜI GIAN XỬ LÝ (PIPELINE) ---
    start_pipeline = time.time()

    # --- BƯỚC 1: DETECT ---
    t1 = time.time()
    detections = detector.detect(frame)
    step1_ms = (time.time() - t1) * 1000
    print(f"[BƯỚC 1] Detect: {step1_ms:.2f} ms | Tìm thấy: {len(detections)}")

    if not detections:
        print("⚠️ Không tìm thấy biển số.")
        cv2.waitKey(0)
        return

    # --- BƯỚC 2: PREPROCESS ---
    t2 = time.time()
    processed_plates = preprocessor.process(frame, detections)
    step2_ms = (time.time() - t2) * 1000
    print(f"[BƯỚC 2] Preprocess: {step2_ms:.2f} ms")

    # --- BƯỚC 3: RECOGNIZE ---
    # 3. RECOGNIZE
    total_ocr_ms = 0
    for i, plate_data in enumerate(processed_plates):
        raw_crop = plate_data['raw_crop']  # Ảnh cắt thô từ YOLO
        processed_img = plate_data['processed_plate']  # Ảnh đã qua xử lý (Threshold + Resize)

        # Show ảnh ban đầu (ảnh đã crop nhưng chưa tiền xử lý)
        cv2.imshow(f"2. Crop Thô {i}", raw_crop)

        # Show ảnh sau khi chuẩn hóa (đây là ảnh đưa vào OCR)
        cv2.imshow(f"3. Chuan Hoa {i}", processed_img)

        plate_img = plate_data['processed_plate']

        t3 = time.time()
        # Gọi Recognizer đọc chữ
        text = recognizer.recognize(plate_img)
        step3_ms = (time.time() - t3) * 1000
        total_ocr_ms += step3_ms
        print(f"[BƯỚC 3] Recognize Biển {i + 1}: {step3_ms:.2f} ms")
        print(f"🔥 KẾT QUẢ: {text}")

    pipeline_duration_ms = (time.time() - start_pipeline) * 1000

    print("-" * 40)
    print(f"📊 TỔNG KẾT HIỆU NĂNG:")
    print(f"  - Tổng thời gian: {pipeline_duration_ms:.2f} ms")
    print(f"  - Tốc độ xử lý:  {1000 / pipeline_duration_ms:.2f} FPS")
    print("-" * 40)

    print("\nNhấn phím bất kỳ trên cửa sổ ảnh để thoát...")
    cv2.waitKey(0)
    cv2.destroyAllWindows()

if __name__ == "__main__":
    test_system()