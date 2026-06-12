from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from decimal import Decimal
from unittest.mock import patch
from fuel_optimizer.models import FuelStation

class RouteOptimizerAPITestCase(APITestCase):
    def setUp(self):
        FuelStation.objects.all().delete()
        # Seed a database fuel station to ensure the route has a stop option
        # Kansas City is roughly in the middle of NY and LA
        FuelStation.objects.create(
            truckstop_id=400,
            name="Kansas City Pilot",
            address="1000 Interstate 70",
            city="Kansas City",
            state="MO",
            retail_price=Decimal("3.15"),
            latitude=39.0997,
            longitude=-94.5786
        )
        
        # We will mock the routing service response to make the test independent of ORS API
        self.mock_route_data = {
            'distance_miles': 2790.0,
            'duration_seconds': 160000.0,
            'coordinates': [
                [40.7128, -74.0060],  # NY
                [39.0997, -94.5786],  # KC
                [34.0522, -118.2437]  # LA
            ],
            'route_polyline': '_p~iF~ps|U_ulLnnqC'
        }

    @patch('fuel_optimizer.services.fuel_optimizer_service.FuelOptimizerService.optimize_route')
    @patch('fuel_optimizer.services.routing_service.RoutingService.get_route')
    def test_successful_route_optimization(self, mock_get_route, mock_optimize):
        """Test API successfully calculates route optimization with mock routing and optimization."""
        mock_get_route.return_value = self.mock_route_data
        mock_optimize.return_value = {
            'distance_miles': 2790.0,
            'fuel_needed_gallons': 279.0,
            'total_cost': 878.85,
            'fuel_stops': [
                {
                    'name': "Kansas City Pilot",
                    'city': "Kansas City",
                    'state': "MO",
                    'price': 3.15,
                    'distance_from_start': 1300,
                    'gallons_purchased': 279.0,
                    'cost': 878.85
                }
            ]
        }
        
        url = reverse('optimize-route')
        data = {
            "start": "New York, NY",
            "finish": "Los Angeles, CA"
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        res_data = response.data
        
        self.assertIn('distance_miles', res_data)
        self.assertIn('estimated_drive_hours', res_data)
        self.assertIn('fuel_needed_gallons', res_data)
        self.assertIn('total_cost', res_data)
        self.assertIn('number_of_stops', res_data)
        self.assertIn('fuel_stops', res_data)
        self.assertIn('route_polyline', res_data)
        self.assertIn('map_data', res_data)
        
        self.assertEqual(res_data['distance_miles'], 2790.0)
        self.assertEqual(res_data['estimated_drive_hours'], 44.44)  # 160000.0 / 3600 = 44.444...
        self.assertEqual(res_data['fuel_needed_gallons'], 279.0)
        self.assertEqual(res_data['number_of_stops'], 1)
        self.assertEqual(len(res_data['fuel_stops']), 1)
        self.assertEqual(res_data['fuel_stops'][0]['name'], "Kansas City Pilot")
        self.assertEqual(res_data['fuel_stops'][0]['price'], 3.15)

    def test_missing_parameters(self):
        """Test API returns 400 when start or finish parameter is missing."""
        url = reverse('optimize-route')
        
        # Missing finish
        response = self.client.post(url, {"start": "New York, NY"}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('finish', response.data)
        
        # Missing start
        response = self.client.post(url, {"finish": "Los Angeles, CA"}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('start', response.data)

    def test_geocoding_failure(self):
        """Test API returns 400 when location cannot be geocoded."""
        url = reverse('optimize-route')
        
        # Use an invalid location name that doesn't match mock or offline coords
        data = {
            "start": "InvalidCityXYZ123",
            "finish": "Los Angeles, CA"
        }
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
        self.assertIn('Unable to geocode start location', response.data['error'])
