from django.contrib import admin
from .models import FuelStation

@admin.register(FuelStation)
class FuelStationAdmin(admin.ModelAdmin):
    list_display = ('truckstop_id', 'name', 'city', 'state', 'retail_price', 'latitude', 'longitude')
    search_fields = ('name', 'city', 'state', 'truckstop_id')
    list_filter = ('state',)
    ordering = ('retail_price',)
