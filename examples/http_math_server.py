#!/usr/bin/env python
"""Simple HTTP MCP server example using FastAPI."""

import json
import logging
from typing import Any, Dict, List
from fastapi import FastAPI, Request, Response
from fastapi.responses import StreamingResponse
import uvicorn

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Tool definitions
TOOLS = [
    {
        "name": "add",
        "description": "Add two numbers",
        "inputSchema": {
            "type": "object",
            "properties": {
                "a": {"type": "number", "description": "First number"},
                "b": {"type": "number", "description": "Second number"}
            },
            "required": ["a", "b"]
        }
    },
    {
        "name": "multiply",
        "description": "Multiply two numbers",
        "inputSchema": {
            "type": "object",
            "properties": {
                "a": {"type": "number", "description": "First number"},
                "b": {"type": "number", "description": "Second number"}
            },
            "required": ["a", "b"]
        }
    },
    {
        "name": "divide",
        "description": "Divide two numbers",
        "inputSchema": {
            "type": "object",
            "properties": {
                "a": {"type": "number", "description": "Dividend"},
                "b": {"type": "number", "description": "Divisor"}
            },
            "required": ["a", "b"]
        }
    }
]


async def handle_request(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """Handle MCP protocol requests."""
    method = request_data.get("method")
    params = request_data.get("params", {})
    request_id = request_data.get("id")
    
    logger.info(f"Handling request: {method}")
    
    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {"listChanged": True}},
                "serverInfo": {"name": "http-math-server", "version": "1.0.0"}
            }
        }
    
    elif method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {"tools": TOOLS}
        }
    
    elif method == "tools/call":
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        
        result = None
        if tool_name == "add":
            result = arguments["a"] + arguments["b"]
        elif tool_name == "multiply":
            result = arguments["a"] * arguments["b"]
        elif tool_name == "divide":
            if arguments["b"] == 0:
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32602,
                        "message": "Cannot divide by zero"
                    }
                }
            result = arguments["a"] / arguments["b"]
        else:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32601,
                    "message": f"Unknown tool: {tool_name}"
                }
            }
        
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "content": [{"type": "text", "text": str(result)}]
            }
        }
    
    else:
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": -32601,
                "message": f"Method not found: {method}"
            }
        }


@app.post("/mcp")
async def mcp_endpoint(request: Request):
    """MCP streamable HTTP endpoint."""
    
    async def generate():
        # Read the request body
        body = await request.body()
        
        # MCP streamable HTTP expects line-delimited JSON
        for line in body.decode().strip().split('\n'):
            if not line:
                continue
                
            try:
                request_data = json.loads(line)
                response = await handle_request(request_data)
                
                # Send response as line-delimited JSON
                yield json.dumps(response) + '\n'
                
            except Exception as e:
                logger.error(f"Error processing request: {e}")
                error_response = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {
                        "code": -32700,
                        "message": f"Parse error: {str(e)}"
                    }
                }
                yield json.dumps(error_response) + '\n'
    
    return StreamingResponse(
        generate(),
        media_type="application/json",
        headers={
            "Content-Type": "application/json",
            "Transfer-Encoding": "chunked"
        }
    )


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "http-math-server"}


if __name__ == "__main__":
    import sys
    
    port = 3000
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            print(f"Invalid port: {sys.argv[1]}, using default {port}")
    
    print(f"Starting HTTP MCP server on port {port}")
    print(f"MCP endpoint: http://localhost:{port}/mcp")
    
    uvicorn.run(app, host="0.0.0.0", port=port)