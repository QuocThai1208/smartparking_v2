from typing import Optional

from rest_framework import viewsets, permissions, status, generics, mixins
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import User, UserRole
from .pagination import EmployeesPagination
from .serializers.token_serializers import TokenSerializer
from .serializers.user_serializers import CustomerRegisterSerializer, UserSerializer, StaffRegisterSerializer, \
    BaseUserSerializer, UpdateEmployeeSerializer, UpdateActiveSerializer
from .serializers import user_serializers
from .services.user_services import UserService
from ..finance.services.finance_service import FinanceService
from . import perms


# view đăng nhập
class LoginView(TokenObtainPairView):
    serializer_class = TokenSerializer


# View đăng ký người dùng mới
class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = (permissions.AllowAny,)
    serializer_class = CustomerRegisterSerializer


# View lấy/ cập nhật thông tin cá nhân yêu cầu token
class UserProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class UserViewSet(viewsets.GenericViewSet):
    queryset = User.objects.filter(is_active=True)
    serializer_class = user_serializers.UserSerializer

    @action(methods=['get'], detail=False, url_path='me/total-payment',
            permission_classes=[permissions.IsAuthenticated])
    def get_total_payment(self, request):
        user = self.request.user
        regimen = self.request.query_params.get("regimen")
        try:
            day = _to_int_or_none(self.request.query_params.get("day"))
            month = _to_int_or_none(self.request.query_params.get("month"))
            year = _to_int_or_none(self.request.query_params.get("year"))
        except ValueError:
            raise ValidationError("ngày, tháng, năm phải là số dương")

        df, dt = FinanceService.create_df_dt(day, month, year)
        revenue = FinanceService.get_total_revenue_range(regimen, user, df, dt)
        payload = {"TotalPayment": revenue}

        if df and dt and df == dt:
            payload.update({"ngày": df.day, "tháng": df.month, "năm": df.year})
        elif df and dt and df.month == 1 and df.day == 1 and dt.month == 12:
            payload.update({"năm": df.year})
        elif df and dt and df.day == 1:
            payload.update({"tháng": df.month, "năm": df.year})
        return Response(payload, status=status.HTTP_200_OK)


class AdminViewSet(viewsets.GenericViewSet):
    permission_classes = [perms.IsManageOrAdmin]
    serializer_class = BaseUserSerializer
    pagination_class = EmployeesPagination

    def get_serializer_class(self):
        if self.action in ["staff_register", "manage_register"]:
            return StaffRegisterSerializer
        return super().get_serializer_class()

    def get_permissions(self):
        if self.action == "manage_register":
            return [perms.IsAdmin()]
        if self.action in ["staff_register", "get_employees"]:
            return [perms.IsManageOrAdmin()]
        if self.action == "get_employees":
            return [perms.IsEmployee()]
        return super().get_permissions()

    def _register_user(self, request, role, success_message):
        serializer = self.get_serializer(data=request.data, context={'role': role})
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        return Response({
            "message": success_message,
            "result": BaseUserSerializer(user).data
        }, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'], url_path='staff/register')
    def staff_register(self, request):
        return self._register_user(request, UserRole.STAFF, "Tạo tài khoản nhân viên thành công.")

    @action(detail=False, methods=['post'], url_path='manage/register')
    def manage_register(self, request):
        return self._register_user(request, UserRole.MANAGE, "Tạo tài khoản quản lý thành công.")

    @action(detail=False, methods=['get'], url_path='employees')
    def get_employees(self, request):
        full_name = request.query_params.get("full_name", "")
        role = request.query_params.get("role", "")

        employees = UserService.get_all_employees(full_name, role)

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(employees, request)

        if page is not None:
            serializer = self.get_serializer(employees, many=True)
            return paginator.get_paginated_response(serializer.data)

        serializer = self.get_serializer(page, many=True)
        return Response({
            "message": "Lấy toàn bộ danh sách nhân viên thành công",
            "result": serializer.data
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='customers')
    def get_customer(self, request):
        full_name = request.query_params.get("full_name", "")
        customers = UserService.get_all_customer(full_name)

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(customers, request)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)

        serializer = self.get_serializer(customers, many=True)
        return Response({
            "message": "Lấy toàn bộ danh sách khách hàng thành công",
            "result": serializer.data
        }, status=status.HTTP_200_OK)

class EmployeeViewSet(viewsets.GenericViewSet, mixins.UpdateModelMixin):
    queryset = User.objects.all()
    serializer_class = BaseUserSerializer

    def get_serializer_class(self):
        if self.action in ['update', 'partial_update']:
            return UpdateEmployeeSerializer
        if self.action == 'update_active':
            return UpdateActiveSerializer
        return super().get_serializer_class()

    def get_permissions(self):
        if self.action in ['update', 'partial_update', 'update_active']:
            return [permissions.IsAuthenticated(), perms.CanUpdateEmployee()]
        return [permissions.IsAuthenticated()]

    @action(detail=True, methods=['patch'], url_path='active')
    def update_active(self, request, pk=None):
        employee = self.get_object()
        serializer = self.get_serializer(employee, data=request.data, partial=True)
        if serializer.is_valid():
            employee_save = serializer.save()
            return Response({
                "message": "Cập nhật active thành công.",
                "result": BaseUserSerializer(employee_save).data
            }, status=status.HTTP_200_OK)
        return Response({
            "detail": "Không thể thực hiện hành động.",
        }, status=status.HTTP_400_BAD_REQUEST)


def _to_int_or_none(value: Optional[str]) -> Optional[int]:
    if value is None or value == '':
        return None
    ivalue = int(value)
    if ivalue <= 0:
        raise ValueError
    return ivalue
