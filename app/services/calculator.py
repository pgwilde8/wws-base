DEFAULT_FUEL_PRICE = 3.90  # NJ/FL average
DEFAULT_MPG = 6.5
DEFAULT_FIXED_COSTS = 200  # $CANDLE fees, insurance per load, etc.


def calculate_break_even(miles, fuel_price=None, mpg=DEFAULT_MPG, fixed_costs=DEFAULT_FIXED_COSTS):
    """
    miles: Total trip miles
    fuel_price: Current average (defaulting to NJ/FL average)
    mpg: Average truck fuel economy
    fixed_costs: $CANDLE fees, insurance per load, etc.
    """
    if fuel_price is None:
        fuel_price = DEFAULT_FUEL_PRICE
    miles = float(miles or 0)
    if miles <= 0:
        miles = 500  # Fallback for unknown mileage

    fuel_cost = (miles / mpg) * fuel_price
    total_cost = fuel_cost + fixed_costs

    # Cost per mile
    cpm = total_cost / miles if miles > 0 else 0

    # Suggested Floor (Cost + 15% margin)
    suggested_floor = total_cost * 1.15

    return {
        "total_cost": round(total_cost, 2),
        "cost_per_mile": round(cpm, 2),
        "suggested_floor": round(suggested_floor, 2),
        "fuel_price": fuel_price,
    }