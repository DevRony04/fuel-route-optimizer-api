def meters_to_miles(meters):
    """Convert meters to miles."""
    return meters * 0.000621371192

def miles_to_meters(miles):
    """Convert miles to meters."""
    return miles / 0.000621371192

def calculate_fuel_gallons(distance_miles, mpg=10.0):
    """Calculate fuel needed in gallons for a given distance in miles."""
    if mpg <= 0:
        raise ValueError("Fuel efficiency (MPG) must be greater than zero.")
    return distance_miles / mpg
