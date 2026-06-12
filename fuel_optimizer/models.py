from django.db import models

class FuelStation(models.Model):
    truckstop_id = models.IntegerField(help_text="Original OPIS Truckstop ID")
    name = models.CharField(max_length=255, help_text="Name of the truck stop")
    address = models.CharField(max_length=255, help_text="Physical address")
    city = models.CharField(max_length=100, help_text="City")
    state = models.CharField(max_length=50, help_text="State abbreviation")
    retail_price = models.DecimalField(
        max_digits=10, 
        decimal_places=4, 
        help_text="Retail price per gallon"
    )
    latitude = models.FloatField(help_text="Latitude coordinate")
    longitude = models.FloatField(help_text="Longitude coordinate")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['city'], name='fs_city_idx'),
            models.Index(fields=['state'], name='fs_state_idx'),
            models.Index(fields=['retail_price'], name='fs_price_idx'),
            models.Index(fields=['latitude'], name='fs_lat_idx'),
            models.Index(fields=['longitude'], name='fs_lon_idx'),
        ]
        verbose_name = "Fuel Station"
        verbose_name_plural = "Fuel Stations"

    def __str__(self):
        return f"{self.name} ({self.city}, {self.state}) - ${self.retail_price:.2f}"
