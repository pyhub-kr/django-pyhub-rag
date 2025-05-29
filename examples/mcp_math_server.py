#!/usr/bin/env python
"""Example MCP server that provides math tools."""

import asyncio
import json
import logging
from typing import Any, Dict

# MCP 서버 구현을 위한 기본 예제
# 실제로는 mcp 패키지의 서버 구현을 사용해야 함

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MathServer:
    """간단한 수학 도구를 제공하는 MCP 서버 예제"""
    
    def __init__(self):
        self.tools = {
            "add": {
                "name": "add",
                "description": "Add two numbers",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "a": {"type": "number", "description": "First number"},
                        "b": {"type": "number", "description": "Second number"}
                    },
                    "required": ["a", "b"]
                }
            },
            "multiply": {
                "name": "multiply",
                "description": "Multiply two numbers",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "a": {"type": "number", "description": "First number"},
                        "b": {"type": "number", "description": "Second number"}
                    },
                    "required": ["a", "b"]
                }
            },
            "power": {
                "name": "power",
                "description": "Calculate a to the power of b",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "base": {"type": "number", "description": "Base number"},
                        "exponent": {"type": "number", "description": "Exponent"}
                    },
                    "required": ["base", "exponent"]
                }
            }
        }
    
    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """요청 처리"""
        method = request.get("method")
        params = request.get("params", {})
        
        if method == "initialize":
            return {
                "protocolVersion": "1.0",
                "capabilities": {
                    "tools": {"listChanged": True}
                }
            }
        
        elif method == "tools/list":
            return {
                "tools": list(self.tools.values())
            }
        
        elif method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments", {})
            
            if tool_name == "add":
                result = arguments["a"] + arguments["b"]
            elif tool_name == "multiply":
                result = arguments["a"] * arguments["b"]
            elif tool_name == "power":
                result = arguments["base"] ** arguments["exponent"]
            else:
                return {"error": f"Unknown tool: {tool_name}"}
            
            return {
                "content": [
                    {"type": "text", "text": str(result)}
                ]
            }
        
        return {"error": f"Unknown method: {method}"}
    
    async def run(self):
        """서버 실행 (stdio 통신)"""
        logger.info("Math MCP server started")
        
        while True:
            try:
                # stdin에서 요청 읽기
                line = await asyncio.get_event_loop().run_in_executor(
                    None, input
                )
                
                if not line:
                    break
                
                # JSON 파싱
                request = json.loads(line)
                logger.info(f"Received request: {request}")
                
                # 요청 처리
                response = await self.handle_request(request)
                
                # stdout으로 응답 전송
                print(json.dumps(response))
                
            except EOFError:
                break
            except Exception as e:
                logger.error(f"Error: {e}")
                error_response = {"error": str(e)}
                print(json.dumps(error_response))
        
        logger.info("Math MCP server stopped")


if __name__ == "__main__":
    server = MathServer()
    asyncio.run(server.run())