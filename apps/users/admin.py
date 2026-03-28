from django.contrib import admin
from .models import User

from ..parking.admin_site import custom_admin_site



class UserAdmin(admin.ModelAdmin):
    list_display   = ('id', 'username', 'full_name', 'email', 'user_role', 'avatar', 'address', 'birth', 'is_staff', 'is_active')
    search_fields  = ('username', 'full_name', 'email')
    list_filter    = ('is_staff', 'is_active')

custom_admin_site.register(User, UserAdmin)