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

Load tools from an MCP server:
```bash
pyhub.llm agent run "Your question" --mcp-server "python /path/to/server.py" --mcp-arg "arg1" --mcp-arg "arg2"
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

## Example MCP Server

See `examples/simple_math_server.py` for a simple example of an MCP server that provides math tools.

## Features

- Dynamic tool loading from external MCP servers
- Automatic JSON Schema to Pydantic model conversion
- Support for filtering specific tools
- Integration with existing pyhub agent system
- Configuration through TOML files or command line