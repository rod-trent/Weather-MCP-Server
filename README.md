# Weather MCP Server

A Model Context Protocol (MCP) server that provides real-time weather data and forecasts for any location worldwide. Built on [Open-Meteo](https://open-meteo.com/) — free, no API key required.

## Tools

| Tool | Description |
|---|---|
| `get_current_weather` | Current conditions: temperature, humidity, wind, pressure, visibility |
| `get_forecast` | Daily forecast up to 16 days: highs/lows, precipitation, wind |
| `get_hourly_forecast` | Hour-by-hour forecast up to 48 hours: temp, rain probability, wind |

## Requirements

- Python 3.10+
- `mcp >= 1.0.0`
- `httpx >= 0.27.0`

## Installation

```bash
git clone https://github.com/rod-trent/Weather-MCP-Server.git
cd Weather-MCP-Server
pip install -r requirements.txt
```

## Configuration

### Claude Desktop

Add the following to your `claude_desktop_config.json`:

**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`  
**macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "weather": {
      "command": "python",
      "args": ["C:/path/to/Weather-MCP-Server/weather_server.py"]
    }
  }
}
```

Replace `C:/path/to/Weather-MCP-Server/` with the actual path where you cloned the repo.

### Claude Code

```bash
claude mcp add weather -- python /path/to/Weather-MCP-Server/weather_server.py
```

Restart Claude after saving the config.

## Usage Examples

Once connected, you can ask Claude things like:

- *"What's the weather in Tokyo right now?"*
- *"Give me a 10-day forecast for London."*
- *"What's the hourly forecast for New York for the next 24 hours?"*

## Data Source

All weather data is sourced from [Open-Meteo](https://open-meteo.com/), a free and open weather API with no rate limits or authentication required.

## License

MIT
