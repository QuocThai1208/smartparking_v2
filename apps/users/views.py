from typing import Optional

from django.shortcuts import render
from rest_framework import viewsets, permissions, status, generics, mixins
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import User
from .serializers.token_serializers import TokenSerializer, RegisterSerializer
from ..finance.serializers import wallet_serializers
from .serializers import user_serializers
from ..finance.services.finance_service import FinanceService


# view đăng nhập
class LoginView(TokenObtainPairView):
    serializer_class = TokenSerializer


# View đăng ký người dùng mới
class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = (permissions.AllowAny,)
    serializer_class = RegisterSerializer


# View lấy/ cập nhật thông tin cá nhân yêu cầu token
class UserProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class UserViewSet(viewsets.GenericViewSet, mixins.ListModelMixin):
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


def _to_int_or_none(value: Optional[str]) -> Optional[int]:
    if value is None or value == '':
        return None
    ivalue = int(value)
    if ivalue <= 0:
        raise ValueError
    return ivalue
