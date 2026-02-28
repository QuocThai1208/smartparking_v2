from ..models import User, Vehicle


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