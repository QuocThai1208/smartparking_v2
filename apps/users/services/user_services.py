from typing import Any

from ..models import User, UserRole


class UserService:
    @staticmethod
    def get_all_employees(full_name: str, role: UserRole) -> Any:
        filters: dict[str, Any] = {
            "user_role__in": [UserRole.STAFF, UserRole.MANAGE],
        }
        if full_name:
            filters["full_name__istartswith"] = full_name
        if role:
            filters.pop("user_role__in", None)
            filters["user_role"] = role
        employees = User.objects.filter(**filters)
        return employees

    @staticmethod
    def get_all_customer(full_name: str) -> Any:
        filters: dict[str, Any] = {
            "user_role": UserRole.CUSTOMER,
        }
        if full_name:
            filters["full_name__istartswith"] = full_name
        customers = User.objects.filter(**filters)
        return customers