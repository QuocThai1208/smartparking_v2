from rest_framework import permissions
from .models import UserRole


class IsVehicleOwner(permissions.IsAuthenticated):
    def has_object_permission(self, request, view, vehicle):
        return super().has_permission(request, view) and request.user == vehicle.user


class IsAdmin(permissions.IsAuthenticated):
    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.user_role == UserRole.ADMIN


class IsStaffOrAdmin(permissions.IsAuthenticated):
    def has_permission(self, request, view):
        return super().has_permission(request, view) and (
                    request.user.user_role == UserRole.STAFF or request.user.user_role == UserRole.ADMIN)


class IsManageOrAdmin(permissions.IsAuthenticated):
    def has_permission(self, request, view):
        return super().has_permission(request, view) and (
                    request.user.user_role == UserRole.MANAGE or request.user.user_role == UserRole.ADMIN)

class IsEmployee(permissions.IsAuthenticated):
    def has_permission(self, request, view):
        return (super().has_permission(request, view) and
                (request.user.user_role == UserRole.MANAGE or
                 request.user.user_role == UserRole.ADMIN or
                 request.user.user_role == UserRole.STAFF
                 ))


class IsStaffOrReadOnly(permissions.IsAuthenticated):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        if not super().has_permission(request, view):
            return False
        return request.user.user_role == UserRole.STAFF or request.user.user_role == UserRole.ADMIN


class CanUpdateEmployee(permissions.BasePermission):
    """
    Quy tắc:
    - Sửa Quản lý (MANAGE): Chỉ ADMIN.
    - Sửa Nhân viên (STAFF): ADMIN hoặc MANAGE.
    """
    message = "Bạn không có quyền thực hiện hành động này."

    def has_object_permission(self, request, view, employee):
        if super().has_permission(request, view):
            user = request.user
            if user.user_role == 'ADMIN':
                return True

            if employee.user_role == 'MANAGE':
                return False

            if employee.user_role == 'STAFF':
                return user.user_role == "MANAGE"
        return False


class IsStaffOrWriteRestricted(permissions.IsAuthenticated):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        if request.method == 'POST':
            return super().has_permission(request, view)
        if not super().has_permission(request, view):
            return False
        return request.user.user_role == UserRole.STAFF or request.user.user_role == UserRole.ADMIN
