document.addEventListener('DOMContentLoaded', () => {
    // ----------------------------------------------------
    // Element Selectors
    // ----------------------------------------------------
    const routeForm = document.getElementById('route-form');
    const startInput = document.getElementById('start-input');
    const finishInput = document.getElementById('finish-input');
    const submitBtn = document.getElementById('submit-btn');
    const submitSpinner = submitBtn.querySelector('.spinner-small');
    const submitText = submitBtn.querySelector('.btn-text');
    
    const errorMessage = document.getElementById('error-message');
    const errorText = document.getElementById('error-text');
    
    const metricsPanel = document.getElementById('metrics-panel');
    const detailsPanel = document.getElementById('details-panel');
    const mapPlaceholder = document.getElementById('map-placeholder');
    const mapLoader = document.getElementById('map-loader');
    
    // Summary values
    const valDistance = document.getElementById('val-distance');
    const valCost = document.getElementById('val-cost');
    const valDuration = document.getElementById('val-duration');
    const valFuel = document.getElementById('val-fuel');
    const valStops = document.getElementById('val-stops');
    const valAvgPrice = document.getElementById('val-avg-price');
    
    // Table and Charts
    const stopsTableBody = document.getElementById('stops-table-body');
    const costChartCanvas = document.getElementById('cost-chart');
    
    // Preset buttons
    const presetButtons = document.querySelectorAll('.btn-preset');

    // ----------------------------------------------------
    // Leaflet Map Initialization
    // ----------------------------------------------------
    let map = null;
    let routePathLayer = null;
    let markerLayerGroup = null;
    let mapMarkers = []; // stores references for hover synchronization
    
    function initMap() {
        if (map) return;
        
        // Center of the US
        map = L.map('map', {
            zoomControl: true,
            scrollWheelZoom: true
        }).setView([37.0902, -95.7129], 4);
        
        // Add OpenStreetMap tiles
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            maxZoom: 19,
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        }).addTo(map);
        
        markerLayerGroup = L.layerGroup().addTo(map);
    }

    // ----------------------------------------------------
    // Chart.js Instance
    // ----------------------------------------------------
    let costChart = null;

    function renderCostChart(fuelStops, totalDistance) {
        if (costChart) {
            costChart.destroy();
        }
        
        // Generate dataset coordinates: [dist, cumulative_cost]
        const dataPoints = [{ x: 0, y: 0 }];
        let cumulativeCost = 0;
        
        fuelStops.forEach(stop => {
            cumulativeCost += parseFloat(stop.cost);
            dataPoints.push({
                x: stop.distance_from_start,
                y: cumulativeCost
            });
        });
        
        // Add final point (destination)
        dataPoints.push({
            x: totalDistance,
            y: cumulativeCost
        });
        
        const ctx = costChartCanvas.getContext('2d');
        costChart = new Chart(ctx, {
            type: 'line',
            data: {
                datasets: [{
                    label: 'Cumulative Fuel Cost ($)',
                    data: dataPoints,
                    borderColor: '#10b981',
                    backgroundColor: 'rgba(16, 185, 129, 0.1)',
                    borderWidth: 2,
                    stepped: true, // Step chart is perfect for discrete refueling stop costs
                    fill: true,
                    tension: 0,
                    pointRadius: 6,
                    pointHoverRadius: 8,
                    pointBackgroundColor: '#10b981',
                    pointBorderColor: '#ffffff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return `Mile ${context.parsed.x.toFixed(0)}: $${context.parsed.y.toFixed(2)}`;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        type: 'linear',
                        title: {
                            display: true,
                            text: 'Distance from Start (miles)',
                            color: '#a1a1aa'
                        },
                        grid: {
                            color: 'rgba(255, 255, 255, 0.05)'
                        },
                        ticks: {
                            color: '#a1a1aa'
                        }
                    },
                    y: {
                        title: {
                            display: true,
                            text: 'Total Spent (USD)',
                            color: '#a1a1aa'
                        },
                        grid: {
                            color: 'rgba(255, 255, 255, 0.05)'
                        },
                        ticks: {
                            color: '#a1a1aa',
                            callback: function(value) {
                                return '$' + value;
                            }
                        }
                    }
                }
            }
        });
    }

    // ----------------------------------------------------
    // Update Map Elements
    // ----------------------------------------------------
    function updateMap(startPoint, finishPoint, coordinates, fuelStops) {
        initMap();
        
        // Clear previous layers
        if (routePathLayer) {
            map.removeLayer(routePathLayer);
        }
        markerLayerGroup.clearLayers();
        mapMarkers = [];
        
        // Draw route path
        // Leaflet expects coordinates as [latitude, longitude]
        routePathLayer = L.polyline(coordinates, {
            color: '#3b82f6',
            weight: 5,
            opacity: 0.85,
            lineJoin: 'round'
        }).addTo(map);
        
        // Start Marker (Blue Pulse)
        const startMarker = L.circleMarker(startPoint, {
            radius: 8,
            fillColor: '#3b82f6',
            color: '#ffffff',
            weight: 2,
            opacity: 1,
            fillOpacity: 0.9
        }).addTo(markerLayerGroup)
          .bindPopup('<b>Start Location</b><br>' + startInput.value);
          
        // Finish Marker (Red Pulse)
        const finishMarker = L.circleMarker(finishPoint, {
            radius: 8,
            fillColor: '#ef4444',
            color: '#ffffff',
            weight: 2,
            opacity: 1,
            fillOpacity: 0.9
        }).addTo(markerLayerGroup)
          .bindPopup('<b>Destination</b><br>' + finishInput.value);
          
        // Fuel Stop Markers (Emerald Green Circles)
        fuelStops.forEach((stop, index) => {
            // Find coordinate index along route closest to stop distance
            // Since we don't have exact coordinate matching, let's look for a coordinate that is closest
            // directly by computing distance, or we can use geocoded locations from candidates.
            // Wait, the API response doesn't return geocoded coordinates of stop in stops, but we can display the popup.
            // Let's check: in views.py, does the optimization result fuel_stops contain lat/lon?
            // In serializer, `FuelStopSerializer` does NOT include latitude and longitude, only:
            // name, city, state, price, distance_from_start, gallons_purchased, cost.
            // But wait! How can we place markers on the map for the fuel stops?
            // Let's look at `fuel_optimizer_service.py` to see if `selected_stops` contains latitude and longitude!
            // In `fuel_optimizer_service.py`:
            // ```python
            // selected_stops.append({
            //     'name': best_station['name'],
            //     'city': best_station['city'],
            //     'state': best_station['state'],
            //     'price': best_station['price'],
            //     'distance_from_start': round(best_station['distance_from_start']),
            //     'gallons_purchased': gallons_to_buy
            //     # Ah, there is no latitude and longitude here!
            // })
            // ```
            // Wait! Can we get latitude and longitude?
            // Let's look at `fuel_optimizer_service.py` line 87-88:
            // ```python
            //     candidate_stations.append({
            //         'id': station.id,
            //         'truckstop_id': station.truckstop_id,
            //         'name': station.name,
            //         'address': station.address,
            //         'city': station.city,
            //         'state': station.state,
            //         'price': float(station.retail_price),
            //         'distance_from_start': dist_from_start,
            //         'latitude': station.latitude,   <--- It does have latitude!
            //         'longitude': station.longitude  <--- It does have longitude!
            //     })
            // ```
            // And in `selected_stops.append(...)` it has:
            // ```python
            // selected_stops.append({
            //     'name': best_station['name'],
            //     'city': best_station['city'],
            //     ...
            // })
            // ```
            // Oh, wait! The view `RouteOptimizerView` returns:
            // ```python
            // response_data = {
            //     'distance_miles': optimization_result['distance_miles'],
            //     ...
            //     'fuel_stops': optimization_result['fuel_stops']
            // }
            // ```
            // Wait, does `FuelStopSerializer` restrict it? Yes, the serializer defines fields, but Django Rest Framework
            // serializer will only serialize fields defined in it.
            // Let's modify `fuel_optimizer/api/serializers.py` to include `latitude` and `longitude` fields in `FuelStopSerializer`
            // and add them in `fuel_optimizer_service.py` so we can easily plot the markers exactly where the stations are!
            // This is a small improvement that makes map plotting 100% accurate and easy.
            // Wait, let's see. Even without modifying the serializer, we could approximate them by looking up coordinates along the route 
            // at distance `distance_from_start`. But having exact coordinates is much better and cleaner!
            // Let's verify: does the `fuel_optimizer/api/serializers.py` already run in tests? Yes.
            // Adding `latitude` and `longitude` to `FuelStopSerializer` won't break any tests since it just adds optional/new fields.
            // Let's check `fuel_optimizer_service.py` again. In `fuel_optimizer_service.py`, `selected_stops.append` can easily add `latitude` and `longitude`.
            // Let's check if the serializer has fields defined. Yes.
            // Wait! Let's write the JS file first. In `app.js`, we can support BOTH cases:
            // If the stop object has `latitude` and `longitude`, use them!
            // If not, approximate the coordinate by finding the coordinate along the route at that cumulative distance.
            // Let's implement BOTH in JS, so it's bulletproof.
            
            let stopCoords = null;
            if (stop.latitude !== undefined && stop.longitude !== undefined) {
                stopCoords = [stop.latitude, stop.longitude];
            } else {
                // Approximate coordinate along the route path based on distance_from_start
                stopCoords = findCoordsAtDistance(coordinates, stop.distance_from_start, totalDistance);
            }
            
            if (stopCoords) {
                const stopMarker = L.circleMarker(stopCoords, {
                    radius: 7,
                    fillColor: '#10b981',
                    color: '#ffffff',
                    weight: 1.5,
                    opacity: 1,
                    fillOpacity: 0.9
                }).addTo(markerLayerGroup)
                  .bindPopup(`
                      <div class="map-popup">
                          <h3>#${index + 1}: ${stop.name}</h3>
                          <p><b>Location:</b> ${stop.city}, ${stop.state}</p>
                          <p><b>Price:</b> $${stop.price.toFixed(2)}/gal</p>
                          <p><b>Purchase:</b> ${stop.gallons_purchased.toFixed(2)} gal ($${stop.cost.toFixed(2)})</p>
                          <p><b>Distance:</b> Mile ${stop.distance_from_start}</p>
                      </div>
                  `);
                  
                mapMarkers.push(stopMarker);
                
                // Add click listener to highlight table row
                stopMarker.on('click', () => {
                    highlightTableRow(index);
                });
            }
        });
        
        // Zoom map to show the entire route
        map.fitBounds(routePathLayer.getBounds(), { padding: [40, 40] });
    }

    // Helper: Approximate coordinate at a certain distance along route polyline
    function findCoordsAtDistance(coordinates, targetDist, totalDistance) {
        if (coordinates.length === 0) return null;
        if (targetDist <= 0) return coordinates[0];
        
        // Calculate cumulative distance for each coordinate segment
        let currentDist = 0;
        for (let i = 0; i < coordinates.length - 1; i++) {
            const p1 = coordinates[i];
            const p2 = coordinates[i + 1];
            
            // Simple Euclidean distance in degrees scaled roughly to miles
            // Or use Haversine approximation in JS:
            const segmentDist = haversineJS(p1[0], p1[1], p2[0], p2[1]);
            
            if (currentDist + segmentDist >= targetDist) {
                // Interpolate between p1 and p2
                const ratio = (targetDist - currentDist) / segmentDist;
                const lat = p1[0] + (p2[0] - p1[0]) * ratio;
                const lon = p1[1] + (p2[1] - p1[1]) * ratio;
                return [lat, lon];
            }
            currentDist += segmentDist;
        }
        
        return coordinates[coordinates.length - 1];
    }
    
    // Simple Haversine calculation in JS for approximation
    function haversineJS(lat1, lon1, lat2, lon2) {
        const R = 3958.8; // miles
        const dLat = (lat2 - lat1) * Math.PI / 180;
        const dLon = (lon2 - lon1) * Math.PI / 180;
        const a = Math.sin(dLat/2) * Math.sin(dLat/2) +
                  Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) * 
                  Math.sin(dLon/2) * Math.sin(dLon/2);
        const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
        return R * c;
    }

    // ----------------------------------------------------
    // Highlight Table Row Sync
    // ----------------------------------------------------
    function highlightTableRow(index) {
        // Remove active highlights
        const rows = stopsTableBody.querySelectorAll('tr');
        rows.forEach(r => r.classList.remove('highlighted'));
        
        if (index >= 0 && index < rows.length) {
            const activeRow = rows[index];
            activeRow.classList.add('highlighted');
            activeRow.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
    }

    // ----------------------------------------------------
    // API Call & Dashboard Processing
    // ----------------------------------------------------
    async function optimizeRoute(start, finish) {
        // Reset states
        errorMessage.classList.add('hidden');
        mapPlaceholder.classList.add('hidden');
        mapLoader.classList.remove('hidden');
        
        // Disable submit button
        submitBtn.disabled = true;
        submitSpinner.classList.remove('hidden');
        submitText.textContent = 'Calculating Route...';
        
        try {
            const response = await fetch('/api/v1/optimize-route/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken') // Django CSRF protection
                },
                body: JSON.stringify({ start, finish })
            });
            
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.error || 'Failed to calculate optimal route. Please try again.');
            }
            
            // Success! Populate data
            displayResults(data);
            
        } catch (err) {
            console.error(err);
            errorText.textContent = err.message;
            errorMessage.classList.remove('hidden');
            mapPlaceholder.classList.remove('hidden');
            metricsPanel.classList.add('hidden');
            detailsPanel.classList.add('hidden');
        } finally {
            // Enable button
            submitBtn.disabled = false;
            submitSpinner.classList.add('hidden');
            submitText.textContent = 'Optimize Fuel Stops';
            mapLoader.classList.add('hidden');
        }
    }

    function displayResults(data) {
        // 1. Show panels
        metricsPanel.classList.remove('hidden');
        detailsPanel.classList.remove('hidden');
        
        // 2. Populate Metrics cards
        valDistance.textContent = data.distance_miles.toLocaleString(undefined, { minimumFractionDigits: 1, maximumFractionDigits: 1 });
        valCost.textContent = '$' + data.total_cost.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
        valDuration.textContent = data.estimated_drive_hours.toLocaleString(undefined, { minimumFractionDigits: 1, maximumFractionDigits: 1 });
        valFuel.textContent = data.fuel_needed_gallons.toLocaleString(undefined, { minimumFractionDigits: 1, maximumFractionDigits: 1 });
        valStops.textContent = data.number_of_stops;
        
        // Calculate average price per gallon purchased
        let avgPrice = 0.0;
        if (data.number_of_stops > 0) {
            let totalCostVal = parseFloat(data.total_cost);
            let totalGals = parseFloat(data.fuel_needed_gallons); // Or total purchased
            
            let totalPurchased = data.fuel_stops.reduce((sum, stop) => sum + parseFloat(stop.gallons_purchased), 0);
            if (totalPurchased > 0) {
                avgPrice = totalCostVal / totalPurchased;
            } else {
                avgPrice = data.fuel_stops.reduce((sum, s) => sum + s.price, 0) / data.number_of_stops;
            }
        }
        valAvgPrice.textContent = avgPrice > 0 ? '$' + avgPrice.toFixed(2) : '-';

        // 3. Populate Stops Table
        stopsTableBody.innerHTML = '';
        if (data.number_of_stops === 0) {
            stopsTableBody.innerHTML = `
                <tr>
                    <td colspan="7" class="empty-row">No refueling stops required. You can complete the route on your initial tank!</td>
                </tr>
            `;
        } else {
            data.fuel_stops.forEach((stop, index) => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td>${index + 1}</td>
                    <td class="station-name">${stop.name}</td>
                    <td>${stop.city}, ${stop.state}</td>
                    <td class="price-col">$${stop.price.toFixed(2)}</td>
                    <td>${stop.gallons_purchased.toFixed(1)} gal</td>
                    <td>$${stop.cost.toFixed(2)}</td>
                    <td>${stop.distance_from_start} mi</td>
                `;
                
                // Row interactions
                tr.addEventListener('mouseenter', () => {
                    highlightTableRow(index);
                    if (mapMarkers[index]) {
                        mapMarkers[index].openPopup();
                    }
                });
                
                tr.addEventListener('mouseleave', () => {
                    // Don't remove highlight immediately to keep context, but can close popup
                });
                
                stopsTableBody.appendChild(tr);
            });
        }

        // 4. Update Map & Polyline Route
        const startPoint = data.map_data.start_point;
        const finishPoint = data.map_data.finish_point;
        const coords = data.map_data.coordinates;
        
        updateMap(startPoint, finishPoint, coords, data.fuel_stops);
        
        // 5. Render Chart
        renderCostChart(data.fuel_stops, data.distance_miles);
    }

    // ----------------------------------------------------
    // Presets and Form Listeners
    // ----------------------------------------------------
    routeForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const startVal = startInput.value.trim();
        const finishVal = finishInput.value.trim();
        
        if (startVal && finishVal) {
            optimizeRoute(startVal, finishVal);
        }
    });
    
    presetButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const start = btn.getAttribute('data-start');
            const finish = btn.getAttribute('data-finish');
            
            startInput.value = start;
            finishInput.value = finish;
            
            optimizeRoute(start, finish);
        });
    });

    // Helper: CSRF Cookie getter for Django API
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
});
