#!/usr/bin/env python
"""Simple weather server example for MCP."""

import sys
import json
import random

# Mock weather data
WEATHER_DATA = {
    "seoul": {"temp": 15, "condition": "Cloudy", "humidity": 65},
    "tokyo": {"temp": 18, "condition": "Sunny", "humidity": 55},
    "newyork": {"temp": 8, "condition": "Rainy", "humidity": 80},
    "nyc": {"temp": 8, "condition": "Rainy", "humidity": 80},
    "london": {"temp": 10, "condition": "Foggy", "humidity": 75},
    "paris": {"temp": 12, "condition": "Partly Cloudy", "humidity": 60},
}

def get_weather(city: str) -> dict:
    """Get weather for a city (mock data)"""
    city_lower = city.lower().replace(" ", "")
    
    if city_lower in WEATHER_DATA:
        return WEATHER_DATA[city_lower]
    else:
        # Random weather for unknown cities
        return {
            "temp": random.randint(-10, 35),
            "condition": random.choice(["Sunny", "Cloudy", "Rainy", "Snowy"]),
            "humidity": random.randint(30, 90)
        }

def main():
    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break
                
            request = json.loads(line.strip())
            method = request.get("method")
            
            if method == "initialize":
                response = {
                    "jsonrpc": "2.0",
                    "id": request.get("id"),
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {"tools": {"listChanged": True}},
                        "serverInfo": {"name": "weather-server", "version": "1.0.0"}
                    }
                }
            
            elif method == "tools/list":
                response = {
                    "jsonrpc": "2.0",
                    "id": request.get("id"),
                    "result": {
                        "tools": [
                            {
                                "name": "get_weather",
                                "description": "Get current weather for a city",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "city": {
                                            "type": "string",
                                            "description": "City name (e.g., Seoul, Tokyo, New York)"
                                        }
                                    },
                                    "required": ["city"]
                                }
                            },
                            {
                                "name": "get_forecast",
                                "description": "Get weather forecast for next 3 days",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "city": {"type": "string"},
                                        "days": {
                                            "type": "integer",
                                            "description": "Number of days (1-3)",
                                            "minimum": 1,
                                            "maximum": 3
                                        }
                                    },
                                    "required": ["city"]
                                }
                            }
                        ]
                    }
                }
            
            elif method == "tools/call":
                params = request.get("params", {})
                tool_name = params.get("name")
                arguments = params.get("arguments", {})
                
                if tool_name == "get_weather":
                    city = arguments.get("city", "Unknown")
                    weather = get_weather(city)
                    result = f"Weather in {city}: {weather['temp']}°C, {weather['condition']}, Humidity: {weather['humidity']}%"
                
                elif tool_name == "get_forecast":
                    city = arguments.get("city", "Unknown")
                    days = arguments.get("days", 3)
                    
                    forecast = []
                    base_weather = get_weather(city)
                    
                    for i in range(min(days, 3)):
                        temp_change = random.randint(-3, 3)
                        forecast.append(f"Day {i+1}: {base_weather['temp'] + temp_change}°C")
                    
                    result = f"Forecast for {city}:\n" + "\n".join(forecast)
                
                else:
                    result = f"Unknown tool: {tool_name}"
                
                response = {
                    "jsonrpc": "2.0",
                    "id": request.get("id"),
                    "result": {
                        "content": [{"type": "text", "text": result}]
                    }
                }
            
            else:
                response = {
                    "jsonrpc": "2.0",
                    "id": request.get("id"),
                    "error": {
                        "code": -32601,
                        "message": f"Method not found: {method}"
                    }
                }
            
            print(json.dumps(response))
            sys.stdout.flush()
            
        except Exception as e:
            error_response = {
                "jsonrpc": "2.0",
                "id": request.get("id") if 'request' in locals() else None,
                "error": {
                    "code": -32603,
                    "message": f"Internal error: {str(e)}"
                }
            }
            print(json.dumps(error_response))
            sys.stdout.flush()

if __name__ == "__main__":
    main()