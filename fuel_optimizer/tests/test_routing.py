from django.test import TestCase
from unittest.mock import patch
from django.core.cache import cache
from fuel_optimizer.services.routing_service import RoutingService
from fuel_optimizer.services.cache_service import CacheService

class RoutingServiceTestCase(TestCase):
    def setUp(self):
        cache.clear()
        self.start_name = "New York, NY"
        self.finish_name = "Los Angeles, CA"
        self.start_coords = (40.7128, -74.0060)
        self.finish_coords = (34.0522, -118.2437)

    def test_mock_fallback_routing(self):
        """Test routing service when ORS API key is missing (fallback to mock)."""
        with patch('django.conf.settings.ORS_API_KEY', ''):
            route = RoutingService.get_route(
                self.start_name,
                self.finish_name,
                self.start_coords,
                self.finish_coords
            )
            self.assertIsNotNone(route)
            self.assertIn('distance_miles', route)
            self.assertIn('duration_seconds', route)
            self.assertIn('coordinates', route)
            self.assertIn('route_polyline', route)
            self.assertGreater(route['distance_miles'], 0)
            self.assertGreater(len(route['coordinates']), 1)

    @patch('requests.post')
    def test_ors_api_routing(self, mock_post):
        """Test routing service when ORS API responds successfully."""
        # Mock ORS API response
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            'routes': [{
                'summary': {
                    'distance': 2790.0,
                    'duration': 144000.0
                },
                'geometry': '_p~iF~ps|U_ulLnnqC_mqNvxq`@'
            }]
        }

        with patch('django.conf.settings.ORS_API_KEY', 'mock-key'):
            route = RoutingService.get_route(
                self.start_name,
                self.finish_name,
                self.start_coords,
                self.finish_coords
            )
            self.assertEqual(route['distance_miles'], 2790.0)
            self.assertEqual(route['duration_seconds'], 144000.0)
            self.assertIsNotNone(route['coordinates'])

    @patch('requests.post')
    def test_routing_cache(self, mock_post):
        """Test that route details are cached and not fetched again."""
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            'routes': [{
                'summary': {
                    'distance': 100.0,
                    'duration': 3600.0
                },
                'geometry': '_p~iF~ps|U_ulLnnqC'
            }]
        }

        with patch('django.conf.settings.ORS_API_KEY', 'mock-key'):
            # First call -> API is called
            route1 = RoutingService.get_route(
                "CityA", "CityB", (40.0, -70.0), (41.0, -71.0)
            )
            
            # Second call -> Cache Hit, API is NOT called again
            route2 = RoutingService.get_route(
                "CityA", "CityB", (40.0, -70.0), (41.0, -71.0)
            )
            
            self.assertEqual(mock_post.call_count, 1)
            self.assertEqual(route1['distance_miles'], route2['distance_miles'])
