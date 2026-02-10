import random
from datetime import datetime

class LoadBoardService:
    @staticmethod
    async def fetch_current_loads():
        # Mocking data that would usually come from a scraper or API
        mock_loads = [
            {"id": 101, "origin": "Elizabeth, NJ", "destination": "Charlotte, NC", "price": 2800, "miles": 630, "type": "Dry Van"},
            {"id": 102, "origin": "Newark, NJ", "destination": "Columbus, OH", "price": 1500, "miles": 530, "type": "Reefer"},
            {"id": 103, "origin": "Jersey City, NJ", "destination": "Atlanta, GA", "price": 3200, "miles": 850, "type": "Flatbed"}
        ]
        return mock_loads

    @staticmethod
    def calculate_profit(load, fuel_price=3.50, mpg=6.5):
        # Your Navy/Business logic goes here
        fuel_cost = (load['miles'] / mpg) * fuel_price
        net_profit = load['price'] - fuel_cost
        return round(net_profit, 2)