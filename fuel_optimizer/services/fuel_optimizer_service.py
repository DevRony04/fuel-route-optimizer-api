import numpy as np
import logging
from django.conf import settings
from fuel_optimizer.models import FuelStation
from fuel_optimizer.utils.geo_utils import project_stations_onto_route
from .cost_calculator import CostCalculator

logger = logging.getLogger(__name__)

class FuelOptimizerService:
    @classmethod
    def optimize_route(cls, route_data):
        """
        Optimize fuel stops for a given route.
        route_data is a dict from RoutingService containing:
          - distance_miles: float
          - duration_seconds: float
          - coordinates: list of [lat, lon]
          - route_polyline: string
        
        Returns a dictionary with:
          - distance_miles: float
          - fuel_needed_gallons: float
          - total_cost: float
          - fuel_stops: list of dicts
        """
        route_coords = np.array(route_data['coordinates'])
        total_distance = route_data['distance_miles']
        
        # 1. Bounding Box Filter to load stations from DB
        # Find min/max lat/lon of route coordinates
        min_lat, min_lon = np.min(route_coords, axis=0)
        max_lat, max_lon = np.max(route_coords, axis=0)
        
        # Add padding (approx. 0.25 degrees is ~17 miles)
        PADDING = 0.25
        
        stations = FuelStation.objects.filter(
            latitude__gte=min_lat - PADDING,
            latitude__lte=max_lat + PADDING,
            longitude__gte=min_lon - PADDING,
            longitude__lte=max_lon + PADDING
        )
        
        logger.info(f"Loaded {stations.count()} stations from DB within bounding box.")
        
        if not stations.exists():
            # If no stations in database, return zero stops unless range is exceeded
            if total_distance > CostCalculator.MAX_RANGE_MILES:
                raise ValueError(
                    f"Unable to complete route: No fuel stations along the route corridor, "
                    f"and destination is beyond maximum range ({CostCalculator.MAX_RANGE_MILES} miles)."
                )
            return {
                'distance_miles': CostCalculator.round_financial(total_distance),
                'fuel_needed_gallons': CostCalculator.fuel_needed_for_distance(total_distance),
                'total_cost': 0.0,
                'fuel_stops': []
            }
            
        # 2. project stations onto route to filter and sort
        station_list = list(stations)
        stations_coords = np.array([[s.latitude, s.longitude] for s in station_list])
        
        # Get distances to route and cumulative distances from start along the route
        min_dists, proj_dists = project_stations_onto_route(stations_coords, route_coords)
        
        # Filter: keep stations within 5.0 miles of the route
        MAX_DIST_FROM_ROUTE = 5.0  # miles
        
        candidate_stations = []
        for idx, station in enumerate(station_list):
            dist_to_route = min_dists[idx]
            dist_from_start = proj_dists[idx]
            
            # Keep stations that are close to the route and lie between start and finish
            if dist_to_route <= MAX_DIST_FROM_ROUTE and 0 < dist_from_start < total_distance:
                candidate_stations.append({
                    'id': station.id,
                    'truckstop_id': station.truckstop_id,
                    'name': station.name,
                    'address': station.address,
                    'city': station.city,
                    'state': station.state,
                    'price': float(station.retail_price),
                    'distance_from_start': dist_from_start,
                    'latitude': station.latitude,
                    'longitude': station.longitude
                })
                
        # Sort stations by distance from start along the route
        candidate_stations.sort(key=lambda x: x['distance_from_start'])
        logger.info(f"Filtered to {len(candidate_stations)} stations along the route corridor.")
        
        # 3. Greedy Refueling Simulation
        max_range = CostCalculator.MAX_RANGE_MILES
        tank_capacity = CostCalculator.TANK_CAPACITY_GALLONS
        mpg = CostCalculator.MPG
        
        if not candidate_stations and total_distance > max_range:
            raise ValueError(
                f"Unable to complete route: No fuel stations along the route corridor, "
                f"and destination is beyond maximum range ({max_range} miles)."
            )

        
        curr_dist = 0.0
        curr_fuel = tank_capacity  # starts with full tank
        selected_stops = []
        last_stop_dist = 0.0
        
        while True:
            # Can we reach the destination directly?
            dist_to_dest = total_distance - curr_dist
            if dist_to_dest <= curr_fuel * mpg:
                # Yes, we can reach the end!
                break
                
            # Find all candidate stations reachable with CURRENT fuel range
            reachable_stations = [
                s for s in candidate_stations 
                if curr_dist < s['distance_from_start'] <= curr_dist + curr_fuel * mpg
            ]
            
            if not reachable_stations:
                logger.warning(f"Stranded at mile {curr_dist}. No reachable fuel stations within range.")
                raise ValueError(
                    f"Unable to complete route: No reachable fuel stations within "
                    f"vehicle range at mile {curr_dist:.1f}."
                )
                
            # Select the cheapest reachable station
            best_station = min(reachable_stations, key=lambda x: x['price'])
            
            # Fuel consumed to reach best_station
            fuel_consumed = (best_station['distance_from_start'] - curr_dist) / mpg
            
            # Since we refuel to full, the gallons purchased at this stop is the fuel
            # consumed to travel from the last stop (or start) to this stop!
            gallons_to_buy = (best_station['distance_from_start'] - last_stop_dist) / mpg
            
            selected_stops.append({
                'name': best_station['name'],
                'city': best_station['city'],
                'state': best_station['state'],
                'price': best_station['price'],
                'distance_from_start': round(best_station['distance_from_start']),
                'gallons_purchased': gallons_to_buy,
                'latitude': best_station['latitude'],
                'longitude': best_station['longitude']
            })
            
            # Move state to best_station
            curr_dist = best_station['distance_from_start']
            last_stop_dist = best_station['distance_from_start']
            curr_fuel = tank_capacity  # refueled to full!

        # Calculate costs and summarize
        summary = CostCalculator.calculate_cost_summary(selected_stops)
        
        # Calculate total fuel needed for route
        fuel_needed = CostCalculator.fuel_needed_for_distance(total_distance)
        
        return {
            'distance_miles': CostCalculator.round_financial(total_distance),
            'fuel_needed_gallons': fuel_needed,
            'total_cost': summary['total_cost'],
            'fuel_stops': selected_stops
        }
