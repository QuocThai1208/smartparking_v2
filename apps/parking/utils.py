import os
import uuid
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile


def save_temp_file(uploaded_file):
    """
    Lưu file từ bộ nhớ tạm xuống đĩa cứng.
    Trả về: Đường dẫn tuyệt đối (Absolute Path) của file.
    """
    if not uploaded_file:
        return None

    # Tạo tên file duy nhất bằng UUID để tránh ghi đè
    ext = os.path.splitext(uploaded_file.name)[1]  # Lấy đuôi file (.jpg, .png)
    unique_filename = f"{uuid.uuid4()}{ext}"

    # 2. Xác định đường dẫn lưu trữ
    # Ví dụ: /media/temp_ai/550e8400-e29b-41d4-a716-446655440000.jpg
    file_path = os.path.join('temp_ai', unique_filename)

    # 3. Sử dụng default_storage để lưu file
    path = default_storage.save(file_path, ContentFile(uploaded_file.read()))

    # 4. Trả về đường dẫn tuyệt đối để Celery Worker có thể tìm thấy file
    return os.path.join(settings.MEDIA_ROOT, path)