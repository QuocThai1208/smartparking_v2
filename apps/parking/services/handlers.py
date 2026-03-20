# import cv2
# import requests
# import time
# from PIL import Image, ImageTk
# from gtts import gTTS
# import io, threading
#
# # Biến toàn cục sẽ được gán từ file main_gui
# arduino = None
# API_URL = None
# cam_in = None
# cam_out = None
# label_captured_in = None
# label_captured_out = None
# label_cam_in = None
# label_cam_out = None
# plate_text_in = None
# plate_text_out = None
# root = None
#
# def init_globals(**kwargs):
#     global arduino, API_URL, cam_in, cam_out
#     global label_captured_in, label_captured_out
#     global label_cam_in, label_cam_out
#     global plate_text_in, plate_text_out, root
#
#     for k, v in kwargs.items():
#         globals()[k] = v
#
#
# def show_captured_image(frame, gate_type):
#     frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
#     img = Image.fromarray(frame_rgb)
#     img = img.resize((280, 200), Image.Resampling.LANCZOS)
#     imgtk = ImageTk.PhotoImage(image=img)
#
#     if gate_type == "IN":
#         label_captured_in.imgtk = imgtk
#         label_captured_in.configure(image=imgtk)
#     elif gate_type == "OUT":
#         label_captured_out.imgtk = imgtk
#         label_captured_out.configure(image=imgtk)
#
# def capture_and_send(cam, event_type):
#     ret, frame = cam.read()
#     if ret:
#         filename = "plate.jpg"
#         cv2.imwrite(filename, frame)
#         show_captured_image(frame, event_type)
#         with open(filename, "rb") as img:
#             files = {"image": img}
#             data = {"direction": event_type}
#             try:
#                 response = requests.post(API_URL, files=files, data=data)
#                 resp_json = response.json()
#                 plate_info = resp_json.get("plate_text")
#                 msg = resp_json.get("msg")
#                 ok = resp_json.get("ok")
#                 if event_type == "IN":
#                     plate_text_in.set(plate_info)
#                 else:
#                     plate_text_out.set(plate_info)
#
#                 # speak_google_async(msg)
#
#                 if ok:
#                     if event_type == 'IN':
#                         arduino.write(b"OPEN_IN\n") # gửi kiểu byte
#                     else:
#                         arduino.write(b"OPEN_OUT\n")
#             except Exception as e:
#                 print("❌ Lỗi gửi ảnh:", e)
#     else:
#         print("❌ Không chụp được ảnh")
#
#
# def arduino_listener():
#     while True:
#         try:
#             line = arduino.readline().decode().strip()
#             if line == "VEHICLE_IN":
#                 capture_and_send(cam_in, "IN")
#             elif line == "VEHICLE_OUT":
#                 capture_and_send(cam_out, "OUT")
#         except Exception as e:
#             print("❌ Lỗi Arduino:", e)
#         time.sleep(0.1)
#
#
# def update_frame():
#     ret1, frame1 = cam_in.read()
#     ret2, frame2 = cam_out.read()
#
#     if ret1:
#         frame1 = cv2.resize(frame1, (320, 240))
#         frame1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2RGB)
#         img1 = Image.fromarray(frame1)
#         imgtk1 = ImageTk.PhotoImage(image=img1)
#         label_cam_in.imgtk = imgtk1
#         label_cam_in.configure(image=imgtk1)
#
#     if ret2:
#         frame2 = cv2.resize(frame2, (320, 240))
#         frame2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2RGB)
#         img2 = Image.fromarray(frame2)
#         imgtk2 = ImageTk.PhotoImage(image=img2)
#         label_cam_out.imgtk = imgtk2
#         label_cam_out.configure(image=imgtk2)
#
#     root.after(30, update_frame)
#
#
# def create_placeholder(size=(250, 250)):
#     img = Image.new("RGB", size, color=(255, 255, 255))
#     return ImageTk.PhotoImage(img)
