from rest_framework import permissions
from .models import UserRole
from ..parking.models import Vehicle


class IsVehicleOwner(permissions.IsAuthenticated):
    def has_object_permission(self, request, view, vehicle):
        return super().has_permission(request, view) and request.user == vehicle.user


class IsLotOwner(permissions.IsAuthenticated):
    def has_object_permission(self, request, view, parkingLot):
        return super().has_permission(request, view) and request.user == parkingLot.owner


class IsAdmin(permissions.IsAuthenticated):
    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.user_role == UserRole.ADMIN


class IsManage(permissions.IsAuthenticated):
    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.user_role == UserRole.MANAGE


class IsCustomer(permissions.IsAuthenticated):
    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.user_role == UserRole.CUSTOMER


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


class IsParkingLotOwner(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if hasattr(obj, 'owner'):
            return obj.owner == request.user

        if hasattr(obj, 'parking_lot'):
            return obj.parking_lot.owner == request.user

        return False


class IsCustomerAndVehicleOwner(permissions.BasePermission):
    def has_permission(self, request, view):
        if view.action == 'create':
            user = request.user

            if hasattr(user, 'user_role') and user.user_role != UserRole.CUSTOMER:
                return False
            vehicle_id = request.data.get('vehicle')
            if not vehicle_id:
                return True

            try:
                vehicle = Vehicle.objects.get(pk=vehicle_id)
                return vehicle.user == request.user
            except Vehicle.DoesNotExist:
                return True

        return True