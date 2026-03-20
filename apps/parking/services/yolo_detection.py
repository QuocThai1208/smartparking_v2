# from ultralytics import YOLO
# import cv2
# from collections import defaultdict
#
# # CẤU HÌNH
# MODEL_PLATE_PATH = "D:/AppParking/Parkingapis/parkingapp/parking/runs/detect/train_bienso/weights/yolo11n_cls_color_vehicle_v1.pt"
# MODEL_CHAR_PATH = "D:/AppParking/Parkingapis/parkingapp/parking/runs/detect/train_ocr/weights/yolo11n_cls_color_vehicle_v1.pt"
# vehicle_model = YOLO('yolov8n.pt')
# VEHICLE_CLASSES = ['car', 'motorcycle', 'bus', 'truck']
# LINE_THRESHOLD = 50
# TARGET_WIDTH = 500
#
#
# # HÀM: Load mô hình
# def load_models():
#     model_plate = YOLO(MODEL_PLATE_PATH)
#     model_char = YOLO(MODEL_CHAR_PATH)
#     return model_plate, model_char
#
#
# # HÀM: Cắt và resize ảnh biển số
# def crop_and_resize_plate(img, box, target_width):
#     x1, y1, x2, y2 = map(int, box)
#     plate_crop = img[y1:y2, x1:x2].copy()
#     h, w = plate_crop.shape[:2]
#
#     if w < target_width:
#         scale = target_width / w
#         plate_crop = cv2.resize(plate_crop, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
#
#     return plate_crop
#
#
# # HÀM: Gom ký tự theo dòng
# def group_characters_by_line(char_data, line_threshold):
#     lines = defaultdict(list)
#     for char in char_data:
#         cy = char['cy']
#         assigned = False
#         for key in lines:
#             if abs(cy - key) < line_threshold:
#                 lines[key].append(char)
#                 assigned = True
#                 break
#         if not assigned:
#             lines[cy].append(char)
#     return lines
#
#
# # HÀM: Nhận diện ký tự từ ảnh biển số
# def recognize_plate_characters(plate_img, model_char):
#     result = model_char(plate_img)[0]
#     boxes = result.boxes
#
#     if boxes is None or len(boxes.cls) == 0:
#         return ""
#
#     char_data = []
#     for i in range(len(boxes.cls)):
#         cx1, cy1, cx2, cy2 = boxes.xyxy[i].tolist()
#         cls_id = int(boxes.cls[i])
#         conf = float(boxes.conf[i])
#         cx = (cx1 + cx2) / 2
#         cy = (cy1 + cy2) / 2
#         char_data.append({
#             'char': model_char.names[cls_id],
#             'conf': conf,
#             'cx': cx,
#             'cy': cy
#         })
#
#     # Gom theo dòng
#     lines = group_characters_by_line(char_data, LINE_THRESHOLD)
#
#     # Sắp xếp từng dòng từ trái sang phải và ghép ký tự
#     sorted_lines = sorted(lines.items(), key=lambda x: x[0])  # top → bottom
#     plate_text = ""
#     for _, chars_in_line in sorted_lines:
#         chars_sorted = sorted(chars_in_line, key=lambda x: x['cx'])
#         plate_text += ''.join([ch['char'] for ch in chars_sorted])
#
#     return plate_text
#
#
# # HÀM CHÍNH: Nhận diện biển số từ ảnh
# def detect_license_plates(image_path: str):
#     model_plate, model_char = load_models()
#     img = cv2.imread(image_path)
#     if img is None:
#         raise FileNotFoundError(f"Không tìm thấy ảnh tại {image_path}")
#
#     result = model_plate(img)[0]
#     if len(result.boxes.xyxy) == 0:
#         return "❌ Không phát hiện biển số."
#
#     for plate_box in result.boxes.xyxy:
#         plate_crop = crop_and_resize_plate(img, plate_box, TARGET_WIDTH)
#         plate_text = recognize_plate_characters(plate_crop, model_char)
#
#         if plate_text:
#             return plate_text
#         else:
#             return "❌ Không phát hiện ký tự."
#
#
# #HÀM: Nhận diện phương tiện
# def detect_vehicle(image_path):
#     results = vehicle_model(image_path)[0]
#     boxes = results.boxes
#     for i in range(len(boxes.cls)):
#         class_id = int(boxes.cls[i])
#         class_name = vehicle_model.names[class_id]
#         if class_name in VEHICLE_CLASSES:
#             return class_name.upper()
#     return None