from decimal import Decimal, ROUND_HALF_UP
from fuel_optimizer.utils.distance_utils import calculate_fuel_gallons

class CostCalculator:
    # Vehicle assumptions
    MPG = 10.0
    TANK_CAPACITY_GALLONS = 50.0  # 500 miles range / 10 MPG
    MAX_RANGE_MILES = 500.0

    @classmethod
    def round_financial(cls, value):
        """Round a float or Decimal value to exactly 2 decimal places."""
        if isinstance(value, float):
            value = Decimal(str(value))
        elif not isinstance(value, Decimal):
            value = Decimal(value)
        return float(value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))

    @classmethod
    def calculate_cost_summary(cls, fuel_stops):
        """
        Calculate total fuel cost based on selected fuel stops.
        fuel_stops is a list of dicts:
        [
           {
              "name": "...",
              "price": 3.12,
              "gallons_purchased": 25.4,
              ...
           }
        ]
        """
        total_cost = Decimal('0.00')
        total_gallons_purchased = Decimal('0.00')
        
        for stop in fuel_stops:
            price = Decimal(str(stop['price']))
            gallons = Decimal(str(stop['gallons_purchased']))
            cost = price * gallons
            
            stop['cost'] = cls.round_financial(cost)
            stop['gallons_purchased'] = float(gallons.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
            
            total_cost += cost
            total_gallons_purchased += gallons
            
        return {
            'total_cost': cls.round_financial(total_cost),
            'total_gallons_purchased': float(total_gallons_purchased.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
        }

    @classmethod
    def fuel_needed_for_distance(cls, distance_miles):
        """Calculate gallons needed for a given distance."""
        return cls.round_financial(calculate_fuel_gallons(distance_miles, cls.MPG))
