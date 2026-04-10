"""
Weather MCP Server
Uses Open-Meteo (free, no API key) for forecasts
and Open-Meteo Geocoding API to resolve city names.
"""

import asyncio
import json
from typing import Any

import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types

app = Server("weather")

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

WMO_CODES = {
    0: "Clear sky",
    1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Fog", 48: "Icy fog",
    51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
    61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
    71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow",
    77: "Snow grains",
    80: "Slight showers", 81: "Moderate showers", 82: "Violent showers",
    85: "Slight snow showers", 86: "Heavy snow showers",
    95: "Thunderstorm", 96: "Thunderstorm with hail", 99: "Thunderstorm with heavy hail",
}


async def geocode(location: str) -> dict:
    """Resolve a place name to lat/lon. Returns dict with lat, lon, name, country."""
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(GEOCODE_URL, params={"name": location, "count": 1, "language": "en", "format": "json"})
        r.raise_for_status()
        data = r.json()

    results = data.get("results")
    if not results:
        raise ValueError(f"Location not found: {location!r}")

    result = results[0]
    return {
        "lat": result["latitude"],
        "lon": result["longitude"],
        "name": result["name"],
        "admin": result.get("admin1", ""),
        "country": result.get("country", ""),
    }


async def fetch_forecast(lat: float, lon: float, days: int = 7) -> dict:
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": [
            "temperature_2m", "relative_humidity_2m", "apparent_temperature",
            "weather_code", "wind_speed_10m", "wind_direction_10m",
            "precipitation", "surface_pressure", "visibility",
        ],
        "daily": [
            "weather_code",
            "temperature_2m_max", "temperature_2m_min", "apparent_temperature_max",
            "precipitation_sum", "precipitation_probability_max",
            "wind_speed_10m_max", "sunrise", "sunset",
        ],
        "hourly": [
            "temperature_2m", "precipitation_probability", "weather_code",
            "wind_speed_10m", "relative_humidity_2m",
        ],
        "temperature_unit": "celsius",
        "wind_speed_unit": "kmh",
        "precipitation_unit": "mm",
        "forecast_days": min(days, 16),
        "timezone": "auto",
    }

    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(FORECAST_URL, params=params)
        r.raise_for_status()
        return r.json()


def format_current(data: dict, location_label: str) -> str:
    cur = data["current"]
    tz = data.get("timezone", "UTC")
    code = cur.get("weather_code", 0)
    condition = WMO_CODES.get(code, "Unknown")

    wind_dir = cur.get("wind_direction_10m", 0)
    compass = ["N","NE","E","SE","S","SW","W","NW"][round(wind_dir / 45) % 8]

    lines = [
        f"Current Weather — {location_label}",
        f"Time zone: {tz}",
        f"As of: {cur['time']}",
        "",
        f"  Condition:    {condition}",
        f"  Temperature:  {cur['temperature_2m']}°C (feels like {cur['apparent_temperature']}°C)",
        f"  Humidity:     {cur['relative_humidity_2m']}%",
        f"  Wind:         {cur['wind_speed_10m']} km/h {compass}",
        f"  Precipitation:{cur['precipitation']} mm",
        f"  Pressure:     {cur['surface_pressure']} hPa",
        f"  Visibility:   {cur.get('visibility', 'N/A')} m",
    ]
    return "\n".join(lines)


def format_daily(data: dict, days: int) -> str:
    daily = data["daily"]
    dates = daily["time"][:days]
    lines = [f"{'Date':<12} {'Condition':<22} {'High':>6} {'Low':>6} {'Rain':>7} {'Rain%':>6} {'Wind':>8}"]
    lines.append("-" * 70)

    for i, date in enumerate(dates):
        code = daily["weather_code"][i]
        condition = WMO_CODES.get(code, "Unknown")
        high = daily["temperature_2m_max"][i]
        low = daily["temperature_2m_min"][i]
        rain = daily["precipitation_sum"][i]
        rain_prob = daily["precipitation_probability_max"][i]
        wind = daily["wind_speed_10m_max"][i]
        lines.append(
            f"{date:<12} {condition:<22} {high:>5.1f}° {low:>5.1f}° {rain:>6.1f}mm {rain_prob:>5}% {wind:>6.0f}km/h"
        )

    return "\n".join(lines)


def format_hourly(data: dict, hours: int = 24) -> str:
    hourly = data["hourly"]
    times = hourly["time"][:hours]
    lines = [f"{'Time':<18} {'Condition':<22} {'Temp':>6} {'Rain%':>6} {'Wind':>8} {'Hum':>5}"]
    lines.append("-" * 70)

    for i, time in enumerate(times):
        code = hourly["weather_code"][i]
        condition = WMO_CODES.get(code, "Unknown")
        temp = hourly["temperature_2m"][i]
        rain_p = hourly["precipitation_probability"][i]
        wind = hourly["wind_speed_10m"][i]
        hum = hourly["relative_humidity_2m"][i]
        lines.append(
            f"{time:<18} {condition:<22} {temp:>5.1f}° {rain_p:>5}% {wind:>6.0f}km/h {hum:>4}%"
        )

    return "\n".join(lines)


# ── Tool definitions ──────────────────────────────────────────────────────────

@app.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="get_current_weather",
            description=(
                "Get the current weather conditions for a location. "
                "Accepts a city name, region, or country."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "City name or place (e.g. 'London', 'New York', 'Tokyo')"
                    }
                },
                "required": ["location"]
            }
        ),
        types.Tool(
            name="get_forecast",
            description=(
                "Get a multi-day daily weather forecast for a location. "
                "Returns high/low temps, precipitation, wind, and conditions for up to 16 days."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "City name or place"
                    },
                    "days": {
                        "type": "integer",
                        "description": "Number of forecast days (1–16, default 7)",
                        "default": 7,
                        "minimum": 1,
                        "maximum": 16
                    }
                },
                "required": ["location"]
            }
        ),
        types.Tool(
            name="get_hourly_forecast",
            description=(
                "Get an hour-by-hour weather forecast for a location. "
                "Returns temperature, precipitation probability, wind, and conditions."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "City name or place"
                    },
                    "hours": {
                        "type": "integer",
                        "description": "Number of hours to show (1–48, default 24)",
                        "default": 24,
                        "minimum": 1,
                        "maximum": 48
                    }
                },
                "required": ["location"]
            }
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[types.TextContent]:
    try:
        location_str = arguments["location"]
        geo = await geocode(location_str)
        location_label = f"{geo['name']}"
        if geo["admin"]:
            location_label += f", {geo['admin']}"
        if geo["country"]:
            location_label += f", {geo['country']}"

        if name == "get_current_weather":
            data = await fetch_forecast(geo["lat"], geo["lon"], days=1)
            text = format_current(data, location_label)

        elif name == "get_forecast":
            days = int(arguments.get("days", 7))
            data = await fetch_forecast(geo["lat"], geo["lon"], days=days)
            current_block = format_current(data, location_label)
            daily_block = format_daily(data, days)
            text = f"{current_block}\n\n{days}-Day Forecast:\n{daily_block}"

        elif name == "get_hourly_forecast":
            hours = int(arguments.get("hours", 24))
            data = await fetch_forecast(geo["lat"], geo["lon"], days=3)
            text = f"Hourly Forecast — {location_label}\n\n{format_hourly(data, hours)}"

        else:
            text = f"Unknown tool: {name}"

    except ValueError as e:
        text = f"Error: {e}"
    except httpx.HTTPError as e:
        text = f"Weather API error: {e}"

    return [types.TextContent(type="text", text=text)]


# ── Entry point ───────────────────────────────────────────────────────────────

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
