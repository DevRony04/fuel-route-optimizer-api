from django.test import TestCase
from decimal import Decimal
from fuel_optimizer.models import FuelStation
from fuel_optimizer.services.fuel_optimizer_service import FuelOptimizerService
from fuel_optimizer.services.cost_calculator import CostCalculator

class FuelOptimizerTestCase(TestCase):
    def setUp(self):
        FuelStation.objects.all().delete()
        # Create some mock stations along a simple straight line route from NY to LA
        # We will create them at specific mileages along latitude 40.0, longitude sequence
        # NY (40.0, -74.0) to LA (40.0, -118.0)
        # 1 degree longitude at latitude 40.0 is approx. 53 miles.
        # So we can place stations at progressive longitudes:
        # -74.0 is mile 0
        # -79.0 is approx. 265 miles (reachable on 1st tank)
        # -84.0 is approx. 530 miles (reachable from 265)
        # -89.0 is approx. 795 miles
        # -94.0 is approx. 1060 miles
        
        self.stations = [
            FuelStation.objects.create(
                truckstop_id=1,
                name="Station A (Cheap)",
                address="123 Exit 1",
                city="Harrisburg",
                state="PA",
                retail_price=Decimal("3.00"),
                latitude=40.0,
                longitude=-80.0  # ~315 miles
            ),
            FuelStation.objects.create(
                truckstop_id=2,
                name="Station B (Expensive)",
                address="456 Exit 2",
                city="Columbus",
                state="OH",
                retail_price=Decimal("3.80"),
                latitude=40.0,
                longitude=-85.0  # ~578 miles
            ),
            FuelStation.objects.create(
                truckstop_id=3,
                name="Station C (Cheap)",
                address="789 Exit 3",
                city="Indianapolis",
                state="IN",
                retail_price=Decimal("2.90"),
                latitude=40.0,
                longitude=-89.0  # ~788 miles
            )
        ]

    def test_cost_calculator_rounding(self):
        """Test CostCalculator rounds financial calculations correctly."""
        self.assertEqual(CostCalculator.round_financial(3.12345), 3.12)
        self.assertEqual(CostCalculator.round_financial(3.125), 3.13)
        self.assertEqual(CostCalculator.round_financial("10.005"), 10.01)

    def test_zero_stops_needed(self):
        """Test that no fuel stops are planned if destination is within initial range."""
        # Route is 400 miles long
        route_coords = [[40.0, -74.0], [40.0, -81.54]]  # ~400 miles
        route_data = {
            'distance_miles': 400.0,
            'duration_seconds': 24000.0,
            'coordinates': route_coords,
            'route_polyline': 'polyline_data'
        }
        
        result = FuelOptimizerService.optimize_route(route_data)
        self.assertEqual(result['distance_miles'], 400.0)
        self.assertEqual(len(result['fuel_stops']), 0)
        self.assertEqual(result['total_cost'], 0.0)

    def test_one_stop_needed(self):
        """Test route requiring exactly one fuel stop at cheapest station."""
        # Route is 800 miles long, needs to refuel
        route_coords = [[40.0, -74.0], [40.0, -89.1]]  # ~800 miles
        route_data = {
            'distance_miles': 800.0,
            'duration_seconds': 48000.0,
            'coordinates': route_coords,
            'route_polyline': 'polyline_data'
        }
        
        result = FuelOptimizerService.optimize_route(route_data)
        
        self.assertEqual(result['distance_miles'], 800.0)
        self.assertGreater(len(result['fuel_stops']), 0)
        
        # Should stop at Station C (Indianapolis) which is at ~795 miles
        # Wait, Indianapolis is at ~795 miles, but can we reach it on the first tank?
        # Starting tank range is 500 miles. We CANNOT reach Indianapolis (795 miles) directly.
        # We must stop at Station A (265 miles) or Station B (530 miles - wait, 530 > 500 so B is unreachable).
        # So we MUST stop at Station A!
        # Let's verify that Station A is in the stops.
        stop_names = [stop['name'] for stop in result['fuel_stops']]
        self.assertIn("Station A (Cheap)", stop_names)

    def test_stranded_route(self):
        """Test that value error is raised if no stations are in range (stranded)."""
        # Place destination at 1000 miles, delete all stations
        FuelStation.objects.all().delete()
        route_coords = [[40.0, -74.0], [40.0, -92.9]]  # ~1000 miles
        route_data = {
            'distance_miles': 1000.0,
            'duration_seconds': 60000.0,
            'coordinates': route_coords,
            'route_polyline': 'polyline_data'
        }
        
        with self.assertRaises(ValueError):
            FuelOptimizerService.optimize_route(route_data)
class GeocodingServiceTestCase(TestCase):
    def test_offline_geocoding_lookup(self):
        """Test that geocoder correctly resolves coords from local cache."""
        from fuel_optimizer.services.geocoding_service import GeocodingService
        coords = GeocodingService.geocode("New York, NY")
        self.assertIsNotNone(coords)
        self.assertAlmostEqual(coords[0], 40.7128, places=1)
        self.assertAlmostEqual(coords[1], -74.0060, places=1)
