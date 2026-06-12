from rest_framework import serializers

class RouteRequestSerializer(serializers.Serializer):
    start = serializers.CharField(
        max_length=255, 
        required=True, 
        help_text="Start location address or city/state (USA), e.g. 'New York, NY'"
    )
    finish = serializers.CharField(
        max_length=255, 
        required=True, 
        help_text="Finish location address or city/state (USA), e.g. 'Los Angeles, CA'"
    )

class FuelStopSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    city = serializers.CharField(max_length=100)
    state = serializers.CharField(max_length=50)
    price = serializers.FloatField(help_text="Fuel price per gallon at this station")
    distance_from_start = serializers.IntegerField(help_text="Distance along the route from start in miles")
    gallons_purchased = serializers.FloatField(help_text="Gallons of fuel purchased at this stop")
    cost = serializers.FloatField(help_text="Total cost of fuel purchased at this stop in USD")
    latitude = serializers.FloatField(required=False, help_text="Latitude coordinate of the station")
    longitude = serializers.FloatField(required=False, help_text="Longitude coordinate of the station")

class MapDataSerializer(serializers.Serializer):
    start_point = serializers.ListField(
        child=serializers.FloatField(), 
        min_length=2, 
        max_length=2, 
        help_text="[latitude, longitude] of start"
    )
    finish_point = serializers.ListField(
        child=serializers.FloatField(), 
        min_length=2, 
        max_length=2, 
        help_text="[latitude, longitude] of finish"
    )
    coordinates = serializers.ListField(
        child=serializers.ListField(child=serializers.FloatField(), min_length=2, max_length=2),
        help_text="Full list of coordinates [lat, lon] representing the route"
    )

class RouteResponseSerializer(serializers.Serializer):
    distance_miles = serializers.FloatField(help_text="Total route distance in miles")
    estimated_drive_hours = serializers.FloatField(help_text="Estimated drive time in hours")
    fuel_needed_gallons = serializers.FloatField(help_text="Total fuel needed in gallons")
    total_cost = serializers.FloatField(help_text="Total fuel cost in USD")
    number_of_stops = serializers.IntegerField(help_text="Total number of refueling stops")
    fuel_stops = FuelStopSerializer(many=True, help_text="List of optimal refueling stops")
    route_polyline = serializers.CharField(help_text="Encoded polyline string of the route")
    map_data = MapDataSerializer(help_text="Map visualization data containing coordinates and points")
