import requests
from django.conf import settings
import uuid
import hashlib
import hmac

class MomoService:
    def __init__(self):
        self.partner_code = settings.MOMO_PARTNER_CODE
        self.access_key = settings.MOMO_ACCESS_KEY
        self.secret_key = settings.MOMO_SECRET_KEY
        self.endpoint = 'https://test-payment.momo.vn/v2/gateway/api/create'
        self.ipn_url = 'https://47a3-123-20-217-17.ngrok-free.app/api/payment-momo/webhook'
        self.return_url = 'exp+parkingmobileapp://wallet'

    def create_payment(self, user_id, amount, description):
        order_id = str(uuid.uuid4())
        request_id = str(uuid.uuid4())
        extra_data = str(user_id)
        request_type = "captureWallet"

        # Tạo chuỗi raw signature theo đúng thứ tự
        raw_signature = (
            f"accessKey={self.access_key}"
            f"&amount={amount}"
            f"&extraData={extra_data}"
            f"&ipnUrl={self.ipn_url}"
            f"&orderId={order_id}"
            f"&orderInfo={description}"
            f"&partnerCode={self.partner_code}"
            f"&redirectUrl={self.return_url}"
            f"&requestId={request_id}"
            f"&requestType={request_type}"
        )
        #Ký HMAC-SHA256
        signature = hmac.new(
            self.secret_key.encode('utf-8'),
            raw_signature.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        #Tạo Payload gửi đi
        payload = {
            'partnerCode': self.partner_code,
            'partnerName': "Test",
            'storeId': "SmartparkingTest",
            'requestId': request_id,
            'amount': int(amount),
            'orderId': order_id,
            'orderInfo': description,
            'redirectUrl': self.return_url,
            'ipnUrl': self.ipn_url,
            'lang': 'vi',
            'extraData': extra_data,
            'requestType': request_type,
            'signature': signature,
        }

        response = requests.post(self.endpoint, json=payload)
        return response.json(), order_id

