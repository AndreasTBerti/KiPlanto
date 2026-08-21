from dotenv import load_dotenv
import os
import requests

load_dotenv()

open_meteo = os.getenv("OPEN_METEO_URL")
geo_encoding = os.getenv("GEO_ENCODING_URL")

def get_coordinates(city: str = "tupã", country_code: str = "BR") -> dict:

    params = {
        "name": city,
        "count": 1,
        "language": "pt",
        "format": "json",
        "countryCode": country_code
        }

    response = requests.get(geo_encoding, params=params, timeout=10)
    response.raise_for_status()

    data: dict = response.json()
    if not data.get("results"):
        raise ValueError(f"Cidade não encontrada: {city}")

    location: dict = data["results"][0]

    return {
        "city": location["name"],
        "country": location.get("country"),
        "latitude": location["latitude"],
        "longitude": location["longitude"],
        "timezone": location.get("timezone")
    }

def get_climate_data(coordinate_data: dict) -> dict:

    latitude = coordinate_data["latitude"]
    longitude = coordinate_data["longitude"]

    params = {
        "latitude": latitude,
        "longitude": longitude,

        "current": [
            "temperature_2m",
            "relative_humidity_2m",
            "wind_speed_10m",
            "wind_direction_10m",
            "precipitation"
        ],

        "daily": [
            "temperature_2m_mean",
            "precipitation_sum",
            "rain_sum"
        ],

        "temperature_unit": "celsius",
        "wind_speed_unit": "kmh",
        "precipitation_unit": "mm",
        "timezone": "auto"
    }

    response = requests.get(open_meteo, params=params, timeout=10)
    response.raise_for_status()

    data: dict = response.json()
    current: dict = data["current"]
    daily: dict = data["daily"]

    next_week_temperature_mean = sum(daily["temperature_2m_mean"]) / len(daily["temperature_2m_mean"])
    next_week_preciptation_sum = sum(daily["precipitation_sum"]) / len(daily["precipitation_sum"])
    next_week_rain_sum = sum(daily["rain_sum"]) / len(daily["rain_sum"])

    return {
        "city": coordinate_data["city"],
        "latitude": latitude,
        "longitude": longitude,

        "temperature": current["temperature_2m"],
        "humidity": current["relative_humidity_2m"],
        "wind_speed": current["wind_speed_10m"],
        "wind_direction": current["wind_direction_10m"],
        "precipitation": current["precipitation"],

        "temperature_forecast": round(next_week_temperature_mean, 2),
        "preciptation_forecast": round(next_week_preciptation_sum, 2),
        "rain_forecast": round(next_week_rain_sum, 2),

        "time": current["time"]
    }

if __name__ == "__main__":

    location = get_coordinates("Tupã")
    weather = get_climate_data(location)

    print(weather)