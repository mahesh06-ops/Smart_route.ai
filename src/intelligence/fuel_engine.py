"""
Fuel Consumption & Cost Engine.
Calculates fuel volume and financial cost based on distance, vehicle type, and mileage.
"""
from typing import Dict, Any, Optional
from src.config.settings import settings


class FuelEngine:
    @staticmethod
    def calculate_fuel(
        distance_km: float,
        vehicle_type: str = "car",
        custom_mileage: Optional[float] = None,
        fuel_price: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Calculates fuel consumed in liters and estimated cost in local currency.
        Formula:
            fuel_liters = distance_km / mileage_km_per_liter
            fuel_cost = fuel_liters * user_defined_fuel_price
        """
        v_type = vehicle_type.lower().strip()
        price = fuel_price if (fuel_price is not None and fuel_price > 0) else settings.DEFAULT_FUEL_PRICE

        if custom_mileage and custom_mileage > 0:
            mileage = custom_mileage
        else:
            mileage = settings.VEHICLE_MILEAGE.get(v_type, settings.VEHICLE_MILEAGE["car"])

        # Prevent division by zero
        if mileage <= 0:
            mileage = 15.0

        fuel_liters = round(distance_km / mileage, 2)
        fuel_cost = round(fuel_liters * price, 2)

        return {
            "vehicle_type": v_type,
            "mileage_km_l": round(mileage, 1),
            "fuel_liters": fuel_liters,
            "fuel_price_per_l": round(price, 2),
            "fuel_cost": fuel_cost,
            "is_live_price": False,  # Transparently indicate standard user-configured price
        }


fuel_engine = FuelEngine()
