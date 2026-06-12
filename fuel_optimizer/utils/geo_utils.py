import numpy as np

def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculate the great circle distance between two points 
    on the earth in miles.
    """
    # Earth radius in miles
    R = 3958.8
    
    phi1 = np.radians(lat1)
    phi2 = np.radians(lat2)
    delta_phi = np.radians(lat2 - lat1)
    delta_lambda = np.radians(lon2 - lon1)
    
    a = (np.sin(delta_phi / 2.0) ** 2 + 
         np.cos(phi1) * np.cos(phi2) * np.sin(delta_lambda / 2.0) ** 2)
    c = 2.0 * np.arctan2(np.sqrt(a), np.sqrt(1.0 - a))
    
    return R * c

def project_stations_onto_route(stations_coords, route_coords):
    """
    Project a list of station coordinates onto a route polyline.
    Returns:
      - min_distances: array of minimum distance in miles from each station to the route.
      - cumulative_distances: array of estimated distance from the start of the route to the projection point.
    
    stations_coords: np.ndarray of shape (N, 2) -> [[lat, lon], ...]
    route_coords: np.ndarray of shape (M, 2) -> [[lat, lon], ...]
    """
    N = len(stations_coords)
    M = len(route_coords)
    
    if N == 0 or M == 0:
        return np.array([]), np.array([])
        
    # Calculate distance along the route segments
    # route_segment_lengths[i] is length of segment between route_coords[i] and route_coords[i+1]
    route_segment_lengths = []
    route_cum_distances = [0.0]
    for i in range(M - 1):
        d = haversine_distance(
            route_coords[i][0], route_coords[i][1],
            route_coords[i+1][0], route_coords[i+1][1]
        )
        route_segment_lengths.append(d)
        route_cum_distances.append(route_cum_distances[-1] + d)
        
    route_segment_lengths = np.array(route_segment_lengths)
    route_cum_distances = np.array(route_cum_distances)
    
    min_distances = np.full(N, fill_value=np.inf)
    proj_distances_from_start = np.zeros(N)
    
    # We will approximate Cartesian coordinates (in miles) locally for each segment
    # to find the closest projection point.
    # 1 degree latitude = 69.0 miles
    # 1 degree longitude = 69.0 * cos(lat) miles
    for i in range(M - 1):
        A = route_coords[i]
        B = route_coords[i+1]
        segment_len = route_segment_lengths[i]
        
        if segment_len == 0:
            continue
            
        # Center lat of the segment
        mid_lat = np.radians((A[0] + B[0]) / 2.0)
        lat_to_miles = 69.0
        lon_to_miles = 69.0 * np.cos(mid_lat)
        
        # Convert segment endpoints to miles relative to A
        B_miles = np.array([
            (B[0] - A[0]) * lat_to_miles,
            (B[1] - A[1]) * lon_to_miles
        ])
        
        # For each station, convert to miles relative to A
        P_miles = np.array([
            (stations_coords[:, 0] - A[0]) * lat_to_miles,
            (stations_coords[:, 1] - A[1]) * lon_to_miles
        ]).T  # shape (N, 2)
        
        # Calculate projection factor t = (P.B) / (B.B)
        # B_miles is shape (2,)
        B_norm_sq = np.sum(B_miles ** 2)
        if B_norm_sq == 0:
            continue
            
        t = np.dot(P_miles, B_miles) / B_norm_sq
        t = np.clip(t, 0.0, 1.0)  # clamp to segment
        
        # Closest point coordinates on segment in miles relative to A
        closest_miles = np.outer(t, B_miles)  # shape (N, 2)
        
        # Distance from station to closest point in miles
        dist_sq = np.sum((P_miles - closest_miles) ** 2, axis=1)
        dist = np.sqrt(dist_sq)
        
        # Distance from A to closest point along the segment
        dist_along_segment = t * segment_len
        
        # Cumulative distance from start of route to closest point
        cum_dist = route_cum_distances[i] + dist_along_segment
        
        # Update minimum distance
        closer = dist < min_distances
        min_distances[closer] = dist[closer]
        proj_distances_from_start[closer] = cum_dist[closer]
        
    return min_distances, proj_distances_from_start
