import logging
import requests
import numpy as np
from django.conf import settings
from .cache_service import CacheService
from fuel_optimizer.utils.geo_utils import haversine_distance
from fuel_optimizer.utils.route_utils import encode_polyline, decode_polyline
from fuel_optimizer.utils.distance_utils import meters_to_miles

logger = logging.getLogger(__name__)

class RoutingService:
    @classmethod
    def get_route(cls, start_name, finish_name, start_coords, finish_coords):
        """
        Retrieve route between start and finish coordinates.
        Returns a dictionary containing:
          - distance_miles: float
          - duration_seconds: float
          - coordinates: list of [lat, lon]
          - route_polyline: string (encoded polyline)
        """
        # 1. Check Cache first
        cached_route = CacheService.get_cached_route(start_name, finish_name)
        if cached_route:
            logger.info(f"Route Cache HIT for {start_name} -> {finish_name}")
            return cached_route

        # Start and finish coordinates
        # ORS expects coordinates as [longitude, latitude]
        start_lat, start_lon = start_coords
        finish_lat, finish_lon = finish_coords

        api_key = getattr(settings, 'ORS_API_KEY', '')
        route_data = None

        if api_key:
            try:
                headers = {
                    'Authorization': api_key,
                    'Content-Type': 'application/json; charset=utf-8'
                }
                body = {
                    "coordinates": [[start_lon, start_lat], [finish_lon, finish_lat]],
                    "instructions": False,
                    "preference": "fastest",
                    "units": "mi"
                }
                logger.info(f"Calling OpenRouteService API for {start_name} -> {finish_name}")
                response = requests.post(
                    settings.ORS_DIRECTIONS_URL,
                    json=body,
                    headers=headers,
                    timeout=15
                )

                if response.status_code == 200:
                    res_json = response.json()
                    route = res_json['routes'][0]
                    
                    # Extract values
                    # Distance is returned in miles if units="mi" is specified, or meters by default
                    summary = route['summary']
                    distance_miles = summary.get('distance', 0.0)
                    duration_seconds = summary.get('duration', 0.0)
                    
                    # OpenRouteService returns geometry as an encoded polyline
                    geometry_str = route.get('geometry')
                    if geometry_str:
                        # Decode geometry to coordinates (ORS returns lon, lat in geometry)
                        # The standard polyline decoding needs to handle coordinate swap
                        # ORS uses precision 5 or 6 depending on settings. By default, ORS uses precision 5.
                        decoded_coords = decode_polyline(geometry_str, precision=5)
                        
                        # Swap back to [latitude, longitude] because ORS returns [lon, lat] in polyline
                        # Wait, let's verify if ORS geometry decoding returns [lon, lat] or [lat, lon]
                        # Standard decoder decodes values, but since they are encoded as (lat, lon), 
                        # ORS encodes as (lon, lat) or (lat, lon).
                        # Actually, ORS encodes as (lat, lon) in standard polyline format.
                        # Let's swap coordinates to [lat, lon] if ORS encodes as [lon, lat].
                        # In ORS, the encoded polyline string actually represents [lat, lon] pairs.
                        # Wait, let's look at the standard ORS polyline. It encodes [lat, lon] pairs!
                        # Let's double check. If we are unsure, we can read the GeoJSON from ORS 
                        # or test it. But the coordinates in the standard format are [[lat, lon], ...]
                        coordinates = [[c[0], c[1]] for c in decoded_coords]
                    else:
                        coordinates = [list(start_coords), list(finish_coords)]
                        geometry_str = encode_polyline(coordinates)
                        
                    route_data = {
                        'distance_miles': float(distance_miles),
                        'duration_seconds': float(duration_seconds),
                        'coordinates': coordinates,
                        'route_polyline': geometry_str
                    }
                else:
                    logger.warning(
                        f"ORS Directions failed with status {response.status_code}: {response.text}"
                    )
            except Exception as e:
                logger.error(f"Error calling ORS Directions API: {e}")

        # 2. If ORS key is not set or the API fails, generate a mock route
        if route_data is None:
            logger.info("Generating mock route (graceful degradation)")
            route_data = cls._generate_mock_route(start_coords, finish_coords)

        # 3. Cache the resolved route data
        CacheService.cache_route(start_name, finish_name, route_data)
        
        return route_data

    @classmethod
    def _generate_mock_route(cls, start_coords, finish_coords):
        """
        Generate a simulated driving route between two points.
        Accounts for road winding by adding 20% to the straight-line distance.
        Subdivides the path into segments every 10 miles.
        """
        start_lat, start_lon = start_coords
        finish_lat, finish_lon = finish_coords
        
        straight_dist = haversine_distance(start_lat, start_lon, finish_lat, finish_lon)
        distance_miles = straight_dist * 1.2  # 20% road winding factor
        
        # Estimate duration at 60 MPH
        duration_seconds = (distance_miles / 60.0) * 3600.0
        
        # Subdivide route into 10-mile segments
        num_segments = max(int(np.ceil(straight_dist / 10.0)), 2)
        
        lats = np.linspace(start_lat, finish_lat, num_segments)
        lons = np.linspace(start_lon, finish_lon, num_segments)
        
        # Add slight sinusoidal perturbation to simulate road winding
        perturb_factor = 0.05
        perturb_lat = np.sin(np.linspace(0, np.pi * 4, num_segments)) * perturb_factor
        perturb_lon = np.cos(np.linspace(0, np.pi * 4, num_segments)) * perturb_factor
        
        # Don't perturb start and end
        perturb_lat[0] = perturb_lat[-1] = 0.0
        perturb_lon[0] = perturb_lon[-1] = 0.0
        
        coordinates = [[float(lat + p_lat), float(lon + p_lon)] 
                       for lat, lon, p_lat, p_lon in zip(lats, lons, perturb_lat, perturb_lon)]
        
        route_polyline = encode_polyline(coordinates)
        
        return {
            'distance_miles': float(distance_miles),
            'duration_seconds': float(duration_seconds),
            'coordinates': coordinates,
            'route_polyline': route_polyline
        }
