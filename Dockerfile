FROM python:3.11-slim

# Thiết lập các biến môi trường cần thiết
# Ngăn Python tạo ra các file .pyc
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Cài đặt các thư viện hệ thống (Dependencies)
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    && apt-get clean

# Tạo và thiết lập thư mục làm việc bên trong Container
WORKDIR /app

# Cài đặt thư viện
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy toàn bộ mã nguồn vào container
COPY . /app/

# Mở cổng cho container
EXPOSE 8000

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]



