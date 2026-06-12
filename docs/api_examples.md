# API Examples

This document provides payload examples for the **Fuel Route Optimizer API**.

---

## 1. Optimize Route Endpoint

Calculates the optimal fuel stops and total fuel cost along a route between two US cities.

*   **Endpoint**: `POST /api/v1/optimize-route/`
*   **Headers**: `Content-Type: application/json`

### Request Payload

```json
{
  "start": "New York, NY",
  "finish": "Los Angeles, CA"
}
```

### Successful Response Payload (200 OK)

```json
{
  "distance_miles": 2790.0,
  "estimated_drive_hours": 46.5,
  "fuel_needed_gallons": 279.0,
  "total_cost": 878.85,
  "number_of_stops": 2,
  "fuel_stops": [
    {
      "name": "Kansas City Pilot",
      "city": "Kansas City",
      "state": "MO",
      "price": 3.15,
      "distance_from_start": 1300,
      "gallons_purchased": 50.0,
      "cost": 157.50
    },
    {
      "name": "Pilot Travel Center #124",
      "city": "Amarillo",
      "state": "TX",
      "price": 3.05,
      "distance_from_start": 1780,
      "gallons_purchased": 48.0,
      "cost": 146.40
    }
  ],
  "route_polyline": "_p~iF~ps|U_ulLnnqC_mqNvxq`@...",
  "map_data": {
    "start_point": [40.7128, -74.0060],
    "finish_point": [34.0522, -118.2437],
    "coordinates": [
      [40.7128, -74.0060],
      [40.6895, -74.1745],
      [...]
    ]
  }
}
```

---

## 2. Error Responses

### A. Geocoding Failure (400 Bad Request)

Returned if either the start or finish location cannot be resolved to coordinates.

```json
{
  "error": "Unable to geocode start location: 'InvalidCityXYZ123'. Please verify the spelling or format."
}
```

### B. Stranded Route (400 Bad Request)

Returned if the vehicle gets stranded due to a gap between fuel stations that exceeds the 500-mile vehicle range.

```json
{
  "error": "Unable to complete route: No reachable fuel stations within vehicle range at mile 1234.5."
}
```

### C. Missing Parameters (400 Bad Request)

Returned if required parameters are missing in the request.

```json
{
  "finish": [
    "This field is required."
  ]
}
```
