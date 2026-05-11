from typing import Optional

from django.conf import settings
from rest_framework import viewsets, permissions, status, generics, mixins
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import User, UserRole, EmployeeProfile
from .pagination import EmployeesPagination
from .serializers.token_serializers import TokenSerializer
from .serializers.user_serializers import CustomerRegisterSerializer, UserSerializer, StaffSerializer, \
    BaseUserSerializer, UpdateEmployeeSerializer, UpdateActiveSerializer
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
    queryset = User.objects.all()

    def get_serializer_class(self):
        if self.action == 'update_active':
            return UpdateActiveSerializer
        return UserSerializer

    @action(detail=True, methods=['patch'], url_path='active')
    def update_active(self, request, pk=None):
        user = self.get_object()
        serializer = self.get_serializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            user_save = serializer.save()
            return Response({
                "message": "Cập nhật active thành công.",
                "result": BaseUserSerializer(user_save).data
            }, status=status.HTTP_200_OK)
        return Response({
            "detail": "Không thể thực hiện hành động.",
        }, status=status.HTTP_400_BAD_REQUEST)

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


class EmployeeViewSet(viewsets.GenericViewSet,
                      mixins.CreateModelMixin,
                      mixins.ListModelMixin):
    permission_classes = [perms.IsManage]
    serializer_class = BaseUserSerializer
    queryset = User.objects.all()
    pagination_class = EmployeesPagination

    def get_serializer_class(self):
        if self.action in ['create', 'list']:
            return StaffSerializer
        if self.action == 'update_active':
            return UpdateActiveSerializer
        return super().get_serializer_class()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response({
            "message": "Tạo tài khoản nhân viên thành công.",
            "result": serializer.data
        }, status=status.HTTP_201_CREATED)

    def list(self, request, *args, **kwargs):
        parking_lot_id = request.query_params.get("parking_lot", "")
        fullname = request.query_params.get("fullname", "")

        if not parking_lot_id:
            return Response(None, status=status.HTTP_200_OK)
        queryset = EmployeeProfile.objects.filter(parking_lot_id=parking_lot_id)

        if fullname:
            queryset = queryset.filter(user__full_name__istartswith=fullname)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

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
