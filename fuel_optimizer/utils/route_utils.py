def decode_polyline(polyline_str, precision=5):
    """
    Decode an encoded polyline string into a list of [lat, lon] coordinates.
    """
    factor = 10 ** precision
    coordinates = []
    index = 0
    lat = 0
    lng = 0
    length = len(polyline_str)
    
    while index < length:
        # Decode Latitude
        shift = 0
        result = 0
        while True:
            byte = ord(polyline_str[index]) - 63
            index += 1
            result |= (byte & 0x1f) << shift
            shift += 5
            if byte < 0x20:
                break
        delta_lat = ~(result >> 1) if (result & 1) else (result >> 1)
        lat += delta_lat
        
        # Decode Longitude
        shift = 0
        result = 0
        while True:
            byte = ord(polyline_str[index]) - 63
            index += 1
            result |= (byte & 0x1f) << shift
            shift += 5
            if byte < 0x20:
                break
        delta_lng = ~(result >> 1) if (result & 1) else (result >> 1)
        lng += delta_lng
        
        coordinates.append([lat / factor, lng / factor])
        
    return coordinates

def _write_value(value):
    value = ~(value << 1) if value < 0 else (value << 1)
    chunks = []
    while value >= 0x20:
        chunks.append(chr((0x20 | (value & 0x1f)) + 63))
        value >>= 5
    chunks.append(chr(value + 63))
    return "".join(chunks)

def encode_polyline(coordinates, precision=5):
    """
    Encode a list of [lat, lon] coordinates into a polyline string.
    """
    factor = 10 ** precision
    output = []
    prev_lat = 0
    prev_lng = 0
    
    for lat, lng in coordinates:
        lat_val = int(round(lat * factor))
        lng_val = int(round(lng * factor))
        
        output.append(_write_value(lat_val - prev_lat))
        output.append(_write_value(lng_val - prev_lng))
        
        prev_lat = lat_val
        prev_lng = lng_val
        
    return "".join(output)
