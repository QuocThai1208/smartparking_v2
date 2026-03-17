from django.contrib import admin
from .models import Vehicle, FeeRule, ParkingLog, VehicleFace
from .admin_site import custom_admin_site

class VehicleAdmin(admin.ModelAdmin):
    list_display  = ('license_plate', 'vehicle_type', 'name', 'user', 'is_approved', 'image')
    search_fields = ('license_plate', 'name', 'user__full_name')
    list_filter   = ('is_approved',)
    autocomplete_fields = ('user',)

class FeeRuleAdmin(admin.ModelAdmin):
    list_display  = ('fee_type', 'amount', 'active', 'effective_from', 'effective_to')
    search_fields = ('fee_type',)
    list_filter   = ('fee_type',)
    ordering      = ('-effective_from',)

class ParkingLogAdmin(admin.ModelAdmin):
    list_display  = ('id', 'user', 'vehicle', 'check_in', 'check_out', 'duration_minutes', 'fee', 'status')
    search_fields = ('id', 'user__full_name', 'vehicle__license_plate')
    list_filter   = ('status',)
    autocomplete_fields = ('user', 'vehicle', 'fee_rule')

class VehicleFaceAdmin(admin.ModelAdmin):
    list_display  = ('id', 'vehicle', 'owner_name', 'relationship', 'face_img', 'face_vector', 'is_default', 'parent')
    search_fields = ('id', 'owner_name')

custom_admin_site.register(Vehicle, VehicleAdmin)
custom_admin_site.register(FeeRule, FeeRuleAdmin)
custom_admin_site.register(ParkingLog, ParkingLogAdmin)
custom_admin_site.register(VehicleFace, VehicleFaceAdmin)