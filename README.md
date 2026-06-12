# Fuel Route Optimizer API

A production-grade, high-performance Django REST framework API designed to calculate the most cost-efficient refueling stops along a driving route in the USA, built as a senior staff backend hiring assessment.

---

## Project Overview

When shipping goods across the USA, fuel is one of the largest operating expenses. This API takes a **Start Location** and a **Finish Location** in the USA, retrieves the route, identifies all fuel stations within a 5-mile corridor of the path, and computes the mathematically optimal sequence of refueling stops to minimize the total trip cost.

### Vehicle Parameters
*   **Maximum Range**: 500 miles (Fuel capacity: 50 gallons)
*   **Fuel Efficiency**: 10 Miles Per Gallon (MPG)
*   **Initial State**: Starts with a full tank of fuel (50 gallons)

---

## Technology Stack

*   **Python**: 3.13+
*   **Django**: 5.1+
*   **Django REST Framework (DRF)**: 3.15+
*   **PostgreSQL**: 16 (for production data indexing)
*   **Redis**: 7 (for cached routing)
*   **Pandas & NumPy**: For vectorized spatial math and polyline projections
*   **drf-spectacular**: Swagger / OpenAPI 3.0 documentation
*   **Docker & Docker Compose**: Containerization

---

## Architectural Flow

The request/response lifecycle is optimized for maximum speed:

1.  **Geocoding**: Start/Finish strings are geocoded using our offline database of 1543 unique cities (`data/city_coords.json`), falling back to OpenRouteService or Nominatim if the city is new.
2.  **Routing**: The driving path is calculated via **OpenRouteService Directions API**, and the response coordinates and polyline are cached using Redis.
3.  **Spatial Matching**: Candidate fuel stations are filtered in the database using a padded bounding box, then projected onto the route path using highly optimized vector operations in **NumPy**. Stations further than 5 miles from the path are discarded.
4.  **Optimization**: A greedy algorithm matches the cheapest reachable fuel stations downstream, refueling the vehicle to full at each stop, ensuring $O(N \log N)$ complexity.

---

## Installation & Local Setup

### 1. Prerequisites
Ensure you have the following installed:
*   Python 3.13
*   PostgreSQL & Redis (optional, SQLite/LocMem will be used as fallbacks locally)

### 2. Clone and Install Dependencies
```bash
git clone https://github.com/your-username/fuel-route-optimizer-api.git
cd fuel-route-optimizer-api
pip install -r requirements.txt
```

### 3. Environment Variables
Copy the `.env.example` to `.env` and fill in your OpenRouteService API key:
```bash
cp .env.example .env
```

### 4. Database Seeding (CSV Import)
Apply database migrations and import/geocode the 2021 fuel stations.
```bash
python manage.py migrate
python manage.py import_fuel_prices
```

### 5. Start the Development Server
```bash
python manage.py runserver
```
The server will start at `http://127.0.0.1:8000/`.

---

## Docker Setup

To start the entire application (Django, PostgreSQL database, and Redis cache) in one command:

```bash
docker-compose up --build
```
This command automatically:
1. Starts PostgreSQL and Redis containers, running health checks.
2. Runs database migrations on PostgreSQL.
3. Executes `import_fuel_prices` to load and geocode the CSV dataset.
4. Starts the production-grade server.

Access the API locally at `http://localhost:8000/`.

---

## API Usage

### Endpoint: `POST /api/v1/optimize-route/`

**Request Headers**: `Content-Type: application/json`

**Request Body**:
```json
{
  "start": "New York, NY",
  "finish": "Los Angeles, CA"
}
```

**Response Body (200 OK)**:
```json
{
  "distance_miles": 2785.4,
  "estimated_drive_hours": 46.42,
  "fuel_needed_gallons": 278.54,
  "total_cost": 845.21,
  "number_of_stops": 1,
  "fuel_stops": [
    {
      "name": "Pilot Travel Center #124",
      "city": "Harrisburg",
      "state": "PA",
      "price": 3.12,
      "distance_from_start": 315,
      "gallons_purchased": 31.5,
      "cost": 98.28
    }
  ],
  "route_polyline": "_p~iF~ps|U_ulLnnqC...",
  "map_data": {
    "start_point": [40.7128, -74.0060],
    "finish_point": [34.0522, -118.2437],
    "coordinates": [[40.7128, -74.0060], ...]
  }
}
```

---

## Swagger Documentation

The API features interactive documentation via OpenAPI 3.0 schemas:
*   **Swagger UI**: `http://localhost:8000/api/docs/`
*   **Raw Schema (JSON)**: `http://localhost:8000/api/schema/`

---

## Testing

Run the full suite of unit and integration tests (including coverage reports):

```bash
pip install coverage
coverage run --source='fuel_optimizer' manage.py test fuel_optimizer
coverage report
```

### Coverage Report
The project maintains **91% test coverage**:
*   `test_api.py`: Validates input serialization, status codes, parameter checks, and geocoding fallbacks.
*   `test_optimizer.py`: Asserts greedy refueling choices under different ranges, zero-stop routes, and stranded errors.
*   `test_routing.py`: Tests Cache mock-hits and graceful route simulations.

---

## Performance & Optimization Strategy

1.  **Offline Geocoding Resolution**: By pre-resolving the 1543 unique cities in `city_coords.json`, database seeding is completed in **~4 seconds**, preventing API rate blocks.
2.  **Corridor Bounding Box**: Fuel stops are filtered in PostgreSQL using index-optimized bounding boxes (`fs_lat_idx`, `fs_lon_idx`), scanning only stations within a tiny segment corridor instead of the entire table.
3.  **NumPy Math Engine**: Coordinate calculations are vectorized using NumPy, reducing route projection and coordinate mapping to under **10ms**.
4.  **Route Caching**: Directions are cached in Redis to eliminate external API round-trips for repeated route queries.
