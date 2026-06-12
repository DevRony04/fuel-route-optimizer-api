import csv
import os
import logging
from pathlib import Path
from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import transaction
from fuel_optimizer.models import FuelStation
from fuel_optimizer.services.geocoding_service import GeocodingService

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Clean and import fuel prices from CSV into the database.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--csv', 
            type=str, 
            help='Path to the fuel prices CSV file. Defaults to data/fuel-prices-for-be-assessment.csv'
        )

    def handle(self, *args, **options):
        # 1. Resolve CSV path
        csv_opt = options.get('csv')
        base_dir = Path(settings.BASE_DIR)
        
        if csv_opt:
            csv_path = Path(csv_opt)
        else:
            csv_path = base_dir / 'data' / 'fuel-prices-for-be-assessment.csv'
            
        if not csv_path.exists():
            self.stderr.write(self.style.ERROR(f"CSV file not found at {csv_path}"))
            return
            
        self.stdout.write(f"Reading fuel prices from {csv_path}...")
        
        # 2. Parse and validate CSV data
        stations_to_import = []
        seen_keys = set()
        skipped_count = 0
        
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for idx, row in enumerate(reader, start=1):
                try:
                    # Extract fields and strip whitespaces
                    truckstop_id_str = row.get('OPIS Truckstop ID')
                    name = row.get('Truckstop Name')
                    address = row.get('Address')
                    city = row.get('City')
                    state = row.get('State')
                    price_str = row.get('Retail Price')
                    
                    # Validate required fields
                    if not all([truckstop_id_str, name, address, city, state, price_str]):
                        skipped_count += 1
                        logger.warning(f"Row {idx}: Missing required fields. Skipping.")
                        continue
                        
                    truckstop_id = int(truckstop_id_str.strip())
                    name = name.strip()
                    address = address.strip()
                    city = city.strip()
                    state = state.strip()
                    price = float(price_str.strip())
                    
                    # Deduplicate based on unique key (truckstop_id, address)
                    # The same station might have multiple pricing rows, we keep the first one
                    unique_key = (truckstop_id, address.lower())
                    if unique_key in seen_keys:
                        skipped_count += 1
                        continue
                    seen_keys.add(unique_key)
                    
                    stations_to_import.append({
                        'truckstop_id': truckstop_id,
                        'name': name,
                        'address': address,
                        'city': city,
                        'state': state,
                        'retail_price': price
                    })
                except (ValueError, TypeError) as e:
                    skipped_count += 1
                    logger.error(f"Row {idx}: Data validation failed ({e}). Skipping.")
                    continue

        self.stdout.write(f"Parsed {len(stations_to_import)} unique stations (skipped {skipped_count} invalid/duplicate rows).")
        self.stdout.write("Resolving coordinates...")
        
        # 3. Resolve coordinates for each station
        final_stations = []
        geocoding_hits = 0
        geocoding_failures = 0
        
        # Keep track of local geocoding cache within this run
        loc_coords_cache = {}
        
        for idx, item in enumerate(stations_to_import, start=1):
            city_state_key = f"{item['city']}, {item['state']}"
            
            # Check run cache first
            if city_state_key in loc_coords_cache:
                coords = loc_coords_cache[city_state_key]
            else:
                # Resolve via GeocodingService (which handles offline cache, ORS, and Nominatim)
                coords = GeocodingService.geocode(city_state_key)
                if coords:
                    loc_coords_cache[city_state_key] = coords
                    geocoding_hits += 1
                else:
                    geocoding_failures += 1
                    logger.error(f"Failed to geocode location: {city_state_key} for station {item['name']}.")
                    continue
                    
            item['latitude'] = coords[0]
            item['longitude'] = coords[1]
            final_stations.append(FuelStation(**item))
            
            if idx % 500 == 0 or idx == len(stations_to_import):
                self.stdout.write(f"  Geocoded {idx}/{len(stations_to_import)} stations...")

        self.stdout.write(f"Resolved coordinates: {geocoding_failures} failures.")
        
        # 4. Bulk Insert into Database
        self.stdout.write("Writing to database...")
        try:
            with transaction.atomic():
                # Clear existing database records
                FuelStation.objects.all().delete()
                # Bulk create new records
                FuelStation.objects.bulk_create(final_stations, batch_size=500)
            self.stdout.write(
                self.style.SUCCESS(f"Successfully imported {len(final_stations)} fuel stations!")
            )
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Database import failed: {e}"))
            logger.exception("Database bulk insert failed")
