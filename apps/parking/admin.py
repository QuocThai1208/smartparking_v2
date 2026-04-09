from django.contrib import admin
from .models import Vehicle, FeeRule, ParkingLog, VehicleFace, ParkingLot, ParkingSlot, Booking, MapSvg
from .admin_site import custom_admin_site

class VehicleAdmin(admin.ModelAdmin):
    list_display  = ('id', 'license_plate', 'type', 'color', 'brand', 'name', 'user', 'is_approved', 'image')
    search_fields = ('license_plate', 'name', 'user__full_name')
    list_filter   = ('is_approved',)
    autocomplete_fields = ('user',)

class FeeRuleAdmin(admin.ModelAdmin):
    list_display  = ('fee_type', 'parking_lot', 'amount', 'active', 'effective_from', 'effective_to')
    search_fields = ('fee_type',)
    list_filter   = ('fee_type',)
    ordering      = ('-effective_from',)

class ParkingLogAdmin(admin.ModelAdmin):
    list_display  = ('id', 'user', 'vehicle', 'vehicle_face', 'check_in', 'check_out', 'duration_minutes', 'fee', 'final_amount_to_pay', 'status')
    search_fields = ('id', 'user__full_name', 'vehicle__license_plate')
    list_filter   = ('status',)
    autocomplete_fields = ('user', 'vehicle', 'fee_rule')

class VehicleFaceAdmin(admin.ModelAdmin):
    list_display  = ('id', 'vehicle', 'owner_name', 'relationship', 'face_img', 'face_vector', 'is_default', 'parent')
    search_fields = ('id', 'owner_name')

class ParkinglotAdmin(admin.ModelAdmin):
    list_display  = ('id', 'owner', 'name', 'address', 'latitude', 'longitude', 'moto_slots', 'car_slots', 'bus_slots', 'truck_slots', 'threshold_release')
    search_fields = ('id', 'owner')

class ParkingSlotAdmin(admin.ModelAdmin):
    list_display  = ('id', 'parking_lot', 'slot_number', 'is_occupied')
    search_fields = ('id', 'parking_lot', 'slot_number')

class BookingAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'vehicle', 'slot', 'status', 'start_time', 'end_time', 'fee', 'task_id', 'overtime_task_id')
    search_fields = ('id', 'user', 'vehicle', 'slot')


class MapSvgAdmin(admin.ModelAdmin):
    list_display = ('id', 'parking_lot', 'map_svg', 'floor', 'floor_display')
    search_fields = ('id', 'parking_lot', 'map_svg')

custom_admin_site.register(Vehicle, VehicleAdmin)
custom_admin_site.register(FeeRule, FeeRuleAdmin)
custom_admin_site.register(ParkingLog, ParkingLogAdmin)
custom_admin_site.register(VehicleFace, VehicleFaceAdmin)
custom_admin_site.register(ParkingSlot, ParkingSlotAdmin)
custom_admin_site.register(ParkingLot, ParkinglotAdmin)
custom_admin_site.register(Booking, BookingAdmin)
custom_admin_site.register(MapSvg, MapSvgAdmin)
