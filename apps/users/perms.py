from rest_framework import permissions
from .models import UserRole


class IsVehicleOwner(permissions.IsAuthenticated):
    def has_object_permission(self, request, view, vehicle):
        return super().has_permission(request, view) and request.user == vehicle.user


class IsStaffOrAdmin(permissions.IsAuthenticated):
    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.user_role == UserRole.STAFF or request.user.user_role == UserRole.ADMIN


class IsStaffOrReadOnly(permissions.IsAuthenticated):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        if not super().has_permission(request, view):
            return False
        return request.user.user_role == UserRole.STAFF or request.user.user_role == UserRole.ADMIN


class IsStaffOrWriteRestricted(permissions.IsAuthenticated):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        if request.method == 'POST':
            return super().has_permission(request, view)
        if not super().has_permission(request, view):
            return False
        return request.user.user_role == UserRole.STAFF or request.user.user_role == UserRole.ADMIN
