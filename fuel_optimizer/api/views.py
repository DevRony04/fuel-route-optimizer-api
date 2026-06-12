from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema
import logging

from .serializers import RouteRequestSerializer, RouteResponseSerializer
from fuel_optimizer.services.geocoding_service import GeocodingService
from fuel_optimizer.services.routing_service import RoutingService
from fuel_optimizer.services.fuel_optimizer_service import FuelOptimizerService

logger = logging.getLogger(__name__)

class RouteOptimizerView(APIView):
    @extend_schema(
        request=RouteRequestSerializer,
        responses={
            200: RouteResponseSerializer,
            400: RouteResponseSerializer, # Error schemas are documented
        },
        summary="Optimize Fuel Stops along Route",
        description="Calculate the optimal fuel stops and total fuel cost along a route between two US cities."
    )
    def post(self, request, *args, **kwargs):
        serializer = RouteRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
        start_name = serializer.validated_data['start']
        finish_name = serializer.validated_data['finish']
        
        logger.info(f"Received route optimization request: {start_name} -> {finish_name}")
        
        # 1. Geocode start location
        start_coords = GeocodingService.geocode(start_name)
        if not start_coords:
            return Response(
                {"error": f"Unable to geocode start location: '{start_name}'. Please verify the spelling or format."},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # 2. Geocode finish location
        finish_coords = GeocodingService.geocode(finish_name)
        if not finish_coords:
            return Response(
                {"error": f"Unable to geocode finish location: '{finish_name}'. Please verify the spelling or format."},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # 3. Retrieve Route
        try:
            route_data = RoutingService.get_route(
                start_name, 
                finish_name, 
                start_coords, 
                finish_coords
            )
        except Exception as e:
            logger.error(f"Routing failed for {start_name} -> {finish_name}: {e}")
            return Response(
                {"error": f"Routing service failed: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # 4. Optimize fuel stops
        try:
            optimization_result = FuelOptimizerService.optimize_route(route_data)
        except ValueError as e:
            # Catch stranded error
            logger.warning(f"Optimization failed: {e}")
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.exception("Unexpected error during fuel stop optimization")
            return Response(
                {"error": f"Fuel stop optimization failed: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # 5. Format and return response
        duration_seconds = route_data.get('duration_seconds', 0.0)
        estimated_drive_hours = round(duration_seconds / 3600.0, 2)
        
        response_data = {
            'distance_miles': optimization_result['distance_miles'],
            'estimated_drive_hours': estimated_drive_hours,
            'fuel_needed_gallons': optimization_result['fuel_needed_gallons'],
            'total_cost': optimization_result['total_cost'],
            'number_of_stops': len(optimization_result['fuel_stops']),
            'fuel_stops': optimization_result['fuel_stops'],
            'route_polyline': route_data['route_polyline'],
            'map_data': {
                'start_point': list(start_coords),
                'finish_point': list(finish_coords),
                'coordinates': route_data['coordinates']
            }
        }
        
        return Response(response_data, status=status.HTTP_200_OK)
