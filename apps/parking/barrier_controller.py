import serial
import time


class BarrierController:
    def __init__(self, port=None, baudrate=9600):
        self.port = port
        self.baudrate = baudrate
        self.ser = None

        self.is_open = False

    def connect(self):
        """Kết nối tới Arduino khi bạn có phần cứng"""
        try:
            self.ser = serial.Serial(self.port, self.baudrate, timeout=1)
            print(f"Đã kết nối với Arduino tại {self.port}")
        except Exception as e:
            print(f"Chưa kết nối được phần cứng: {e}")

    def process_barrier(self, signal):
        """
        Giai đoạn 2 & 3: Nhận tín hiệu và ra lệnh cho Servo
        signal: 1 (Xe đến/Hợp lệ) hoặc 0 (Xe đi/Không hợp lệ)
        """
        if signal == 1 and not self.is_open:
            print("[GĐ 3] Phát hiện xe: Đang mở thanh chắn (90°)...")
            self._send_to_arduino("OPEN")
            self.is_open = True

        elif signal == 0 and self.is_open:
            print("[GĐ 3] Xe đã qua: Đang đóng thanh chắn (0°)...")
            self._send_to_arduino("CLOSE")
            self.is_open = False

# --- CHẠY THỬ NGHIỆM (MOCK TEST) ---
barrier = BarrierController()

print("--- Test: Xe tiến vào ---")
barrier.process_barrier(1) # Giả lập nhận tín hiệu xe vào

time.sleep(2) # Đợi 2 giây xe đi qua

print("\n--- Test: Xe đã vào xong ---")
barrier.process_barrier(0) # Giả lập nhận tín hiệu xe đã qua