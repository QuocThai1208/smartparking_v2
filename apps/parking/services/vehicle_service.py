from typing import Any

from ..models import User, Vehicle, FeeType
from ..AI_client.predict_vehicle_client import PredictVehicleClient


class VehicleService:
    @staticmethod
    def get_user_vehicle_stats(user: User):
        vehicles = Vehicle.objects.filter(user=user)
        total = vehicles.count()
        approved = vehicles.filter(is_approved=True).count()
        pending = vehicles.filter(is_approved=False).count()
        return {
            'total': total or 0,
            'approved': approved or 0,
            'pending': pending or 0
        }

    @staticmethod
    def create_vehicle(user, name, image_front, image_plate):
        """
        Xử lý ảnh qua Pipeline và lưu Vehicle
        """

        # Reset con trỏ file sau khi read để Cloudinary vẫn lưu được ảnh
        image_front.seek(0)

        res = PredictVehicleClient.prodict_vehicle(image_front, image_plate)

        type_data = res['attributes']['type']

        if type_data is None:
            raise ValueError("detail", "Không thể nhận diện được loại xe.")
        print("type_data", type_data)

        if not type_data in FeeType.values:
            raise ValueError("detail", "Loại xe không hợp lệ.")

        vehicle = Vehicle.objects.create(
            user=user,
            name=name,
            license_plate=res['plate'],
            type=type_data,
            color=res['attributes']['color'] or None,
            brand=res['attributes']['brand'] or None,
            image=image_front
        )
        return vehicle

    @staticmethod
    def get_all_vehicle(license_plate:str, is_approved: bool):
        filters: dict[str, Any] = {}

        if license_plate:
            filters["license_plate"] = license_plate
        if is_approved:
            filters["is_approved"] = is_approved
        vehicles = Vehicle.objects.filter(**filters)
        return vehicles
