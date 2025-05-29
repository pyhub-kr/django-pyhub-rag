# MCP (Model Context Protocol) Integration

pyhub now supports loading tools from MCP servers, allowing you to extend agent capabilities with external tool providers.

## Installation

MCP support is optional. Install with:
```bash
pip install django-pyhub-rag[mcp]
# or
pip install mcp
```

## Usage

### Command Line

#### Single Server
Load tools from a single MCP server:
```bash
pyhub.llm agent run "Your question" --mcp-server "python" --mcp-arg "/path/to/server.py"
```

#### Multiple Servers
Load tools from multiple MCP servers using a config file:
```bash
pyhub.llm agent run "Your question" --mcp-config "examples/mcp_config.toml"
```

### Configuration File

Configure MCP servers in `~/.pyhub.toml`:

```toml
[mcp.servers.math]
command = "python"
args = ["/path/to/math_server.py"]
# env = { PYTHONPATH = "/custom/path" }  # Optional: environment variables
# filter_tools = ["add", "multiply"]  # Optional: load specific tools only

[mcp.servers.web]
command = "node"
args = ["/path/to/web_search_server.js"]
```

### Python API

#### Single Server
```python
from pyhub.llm.agents.mcp import load_mcp_tools
from mcp import StdioServerParameters

# Create server parameters
server_params = StdioServerParameters(
    command="python",
    args=["/path/to/server.py"]
)

# Load tools from MCP server
tools = await load_mcp_tools(server_params)

# Use with agent
agent = create_react_agent(llm=llm, tools=tools)
```

#### Multiple Servers
```python
from pyhub.llm.agents.mcp import MultiServerMCPClient

client = MultiServerMCPClient({
    "math": {"command": "python", "args": ["math_server.py"]},
    "weather": {"command": "python", "args": ["weather_server.py"]}
})

async with client:
    tools = await client.get_tools()
    agent = create_react_agent(llm=llm, tools=tools)
```

## Example MCP Servers

- `examples/simple_math_server.py` - Math calculation tools (add, multiply)
- `examples/weather_server.py` - Weather information tools (get_weather, get_forecast)
- `examples/mcp_config.toml` - Example configuration for multiple servers

## Features

- Dynamic tool loading from external MCP servers
- **Multi-server support**: Load tools from multiple MCP servers simultaneously
- Automatic JSON Schema to Pydantic model conversion
- Support for filtering specific tools
- Integration with existing pyhub agent system
- Configuration through TOML files or command line
- Optional tool name prefixing to avoid conflicts
- Graceful handling of server connection failures