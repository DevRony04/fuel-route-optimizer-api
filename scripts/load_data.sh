#!/bin/bash
# Script to migrate database and load fuel station dataset

set -e

echo "============================================="
echo " Fuel Route Optimizer - Seeding Data         "
echo "============================================="

# 1. Run migrations
echo "Running database migrations..."
python manage.py migrate

# 2. Import fuel stations CSV
echo "Importing fuel prices and geocoding stations..."
python manage.py import_fuel_prices

echo "Data loading completed successfully!"
echo "============================================="
