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

#### Single Server (stdio)
Load tools from a single MCP server via stdio:
```bash
pyhub.llm agent run "Your question" --mcp-server "python" --mcp-arg "/path/to/server.py"
```

#### Single Server (HTTP)
Load tools from a single MCP server via HTTP:
```bash
pyhub.llm agent run "Your question" --mcp-server-http "http://localhost:3000/mcp"
```

#### Multiple Servers
Load tools from multiple MCP servers using a config file:
```bash
pyhub.llm agent run "Your question" --mcp-config "examples/mcp_config.toml"
```

### Configuration File

Configure MCP servers in `~/.pyhub.toml`:

```toml
# stdio transport (default)
[mcp.servers.math]
command = "python"
args = ["/path/to/math_server.py"]
# env = { PYTHONPATH = "/custom/path" }  # Optional: environment variables
# filter_tools = ["add", "multiply"]  # Optional: load specific tools only

# HTTP transport
[mcp.servers.math_http]
transport = "streamable_http"
url = "http://localhost:3000/mcp"
# headers = { "Authorization" = "Bearer token" }  # Optional: HTTP headers

# Transport type is inferred from fields
[mcp.servers.web]
url = "http://localhost:8080/mcp"  # Automatically uses streamable_http
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

### stdio Servers
- `examples/simple_math_server.py` - Math calculation tools (add, multiply)
- `examples/weather_server.py` - Weather information tools (get_weather, get_forecast)

### HTTP Servers
- `examples/http_math_server.py` - HTTP-based math server with FastAPI

### Configuration Examples
- `examples/mcp_config.toml` - Basic multi-server configuration
- `examples/mcp_mixed_config.toml` - Mixed transport types (stdio + HTTP)

## Features

- Dynamic tool loading from external MCP servers
- **Multi-server support**: Load tools from multiple MCP servers simultaneously
- **Multiple transport types**:
  - stdio: Standard I/O communication (default)
  - streamable_http: HTTP-based communication for web services
- Automatic JSON Schema to Pydantic model conversion
- Support for filtering specific tools
- Integration with existing pyhub agent system
- Configuration through TOML files or command line
- Optional tool name prefixing to avoid conflicts
- Graceful handling of server connection failures
- Automatic transport type inference from configuration