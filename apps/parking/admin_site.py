from django.contrib import admin

class ParkingAppAdminSite(admin.AdminSite):
    site_header = 'Hệ thống quản lý giữ xe tự động'
    site_title = 'Admin Smart Parking'
    index_title = 'Bảng điều khiển hệ thống'

# Khởi tạo MỘT biến duy nhất để các app khác dùng chung
custom_admin_site = ParkingAppAdminSite(name='myadmin')