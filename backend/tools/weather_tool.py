import requests


GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
WEATHER_URL = "https://api.open-meteo.com/v1/forecast"


def weather_description(code):
    descriptions = {
        0: "Clear sky",
        1: "Mainly clear",
        2: "Partly cloudy",
        3: "Overcast",

        45: "Foggy",
        48: "Depositing rime fog",

        51: "Light drizzle",
        53: "Moderate drizzle",
        55: "Dense drizzle",

        56: "Light freezing drizzle",
        57: "Dense freezing drizzle",

        61: "Light rain",
        63: "Moderate rain",
        65: "Heavy rain",

        66: "Light freezing rain",
        67: "Heavy freezing rain",

        71: "Light snowfall",
        73: "Moderate snowfall",
        75: "Heavy snowfall",

        77: "Snow grains",

        80: "Light rain showers",
        81: "Moderate rain showers",
        82: "Violent rain showers",

        85: "Light snow showers",
        86: "Heavy snow showers",

        95: "Thunderstorm",
        96: "Thunderstorm with slight hail",
        99: "Thunderstorm with heavy hail"
    }

    return descriptions.get(code, "Unknown conditions")

def get_weather(location: str):
    """
    Get current weather for any city/location.

    Example:
        get_weather("Hyderabad")
        get_weather("Tokyo")
        get_weather("New York")
    """

    try:
        # ----------------------------------------------------
        # STEP 1: Convert city name -> latitude/longitude
        # ----------------------------------------------------

        geo_params = {
            "name": location,
            "count": 1,
            "language": "en",
            "format": "json"
        }

        geo_response = requests.get(
            GEOCODING_URL,
            params=geo_params,
            timeout=10
        )

        geo_response.raise_for_status()

        geo_data = geo_response.json()

        if not geo_data.get("results"):
            return {
                "success": False,
                "error": f"I couldn't find the location '{location}'."
            }

        place = geo_data["results"][0]

        latitude = place["latitude"]
        longitude = place["longitude"]

        city = place.get("name", location)
        country = place.get("country", "")

        # ----------------------------------------------------
        # STEP 2: Get weather using coordinates
        # ----------------------------------------------------

        weather_params = {
            "latitude": latitude,
            "longitude": longitude,
            "current": (
                "temperature_2m,"
                "relative_humidity_2m,"
                "apparent_temperature,"
                "precipitation,"
                "weather_code,"
                "wind_speed_10m"
            ),
            "timezone": "auto"
        }

        weather_response = requests.get(
            WEATHER_URL,
            params=weather_params,
            timeout=10
        )

        weather_response.raise_for_status()

        weather_data = weather_response.json()

        current = weather_data["current"]

        return {
            "success": True,
            "location": f"{city}, {country}",
            "temperature": current.get("temperature_2m"),
            "feels_like": current.get("apparent_temperature"),
            "humidity": current.get("relative_humidity_2m"),
            "precipitation": current.get("precipitation"),
            "wind_speed": current.get("wind_speed_10m"),
            "condition": weather_description(
                current.get("weather_code")),
            "timezone": weather_data.get("timezone")
        }

    except requests.RequestException as e:
        return {
            "success": False,
            "error": f"Weather service unavailable: {e}"
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }