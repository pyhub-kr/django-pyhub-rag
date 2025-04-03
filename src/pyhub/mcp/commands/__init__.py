import logging
import os
from pathlib import Path
from typing import Optional

import typer
from asgiref.sync import async_to_sync
from django.db.models.enums import TextChoices
from mcp.types import Prompt as MCPPrompt
from mcp.types import Resource as MCPResource
from mcp.types import ResourceTemplate as MCPResourceTemplate
from mcp.types import Tool as MCPTool
from pydantic import BaseModel, ValidationError
from rich.console import Console
from rich.table import Table

from pyhub import init, print_for_main
from pyhub.llm.json import json_loads, JSONDecodeError
from pyhub.mcp import mcp

logger = logging.getLogger(__name__)

app = typer.Typer()
console = Console()


logo = """
    ██████╗  ██╗   ██╗ ██╗  ██╗ ██╗   ██╗ ██████╗     ███╗   ███╗ ██████╗██████╗ 
    ██╔══██╗ ╚██╗ ██╔╝ ██║  ██║ ██║   ██║ ██╔══██╗    ████╗ ████║██╔════╝██╔══██╗
    ██████╔╝  ╚████╔╝  ███████║ ██║   ██║ ██████╔╝    ██╔████╔██║██║     ██████╔╝
    ██╔═══╝    ╚██╔╝   ██╔══██║ ██║   ██║ ██╔══██╗    ██║╚██╔╝██║██║     ██╔═══╝ 
    ██║         ██║    ██║  ██║ ╚██████╔╝ ██████╔╝    ██║ ╚═╝ ██║╚██████╗██║     
    ╚═╝         ╚═╝    ╚═╝  ╚═╝  ╚═════╝  ╚═════╝     ╚═╝     ╚═╝ ╚═════╝╚═╝     
"""

app.callback(invoke_without_command=True)(print_for_main(logo))


class ListType(TextChoices):
    TOOLS = "tools"
    RESOURCES = "resources"
    RESOURCE_TEMPLATES = "resource_templates"
    PROMPTS = "prompts"
    ALL = "all"


@app.command()
def inspector():
    """Run inspector using npx"""
    os.system("npx @modelcontextprotocol/inspector")


@app.command(name="list")
def list_(
    list_type: ListType = typer.Argument(ListType.ALL),
    is_verbose: bool = typer.Option(False, "--verbose"),
    toml_path: Optional[Path] = typer.Option(
        Path.home() / ".pyhub.toml",
        "--toml-file",
        help="toml 설정 파일 경로 (디폴트: ~/.pyhub.toml)",
    ),
    env_path: Optional[Path] = typer.Option(
        Path.home() / ".pyhub.env",
        "--env-file",
        help="환경 변수 파일(.env) 경로 (디폴트: ~/.pyhub.env)",
    ),
):
    """장고 프로젝트에 등록된 tools/resources/resource_templates/prompts 목록 조회"""
    log_level = logging.DEBUG if is_verbose else logging.INFO
    init(debug=True, log_level=log_level, toml_path=toml_path, env_path=env_path)

    if list_type in (ListType.TOOLS, ListType.ALL):
        tools: list[MCPTool] = async_to_sync(mcp.list_tools)()
        print_as_table("tools", tools)
        console.print()

    if list_type in (ListType.RESOURCES, ListType.ALL):
        resources: list[MCPResource] = async_to_sync(mcp.list_resources)()
        print_as_table("resources", resources)
        console.print()

    if list_type in (ListType.RESOURCE_TEMPLATES, ListType.ALL):
        resource_templates: list[MCPResourceTemplate] = async_to_sync(mcp.list_resource_templates)()
        print_as_table("resource_templates", resource_templates)
        console.print()

    if list_type in (ListType.PROMPTS, ListType.ALL):
        prompts: list[MCPPrompt] = async_to_sync(mcp.list_prompts)()
        print_as_table("prompts", prompts)
        console.print()


@app.command()
def call_tool(
    tool_name: str = typer.Argument(..., help="tool name"),
    tool_args: list[str] = typer.Argument(
        None, help="Arguments for the tool in key=value format (e.g., x=10 y='hello world')"
    ),
    is_verbose: bool = typer.Option(False, "--verbose"),
    toml_path: Optional[Path] = typer.Option(
        Path.home() / ".pyhub.toml",
        "--toml-file",
        help="toml 설정 파일 경로 (디폴트: ~/.pyhub.toml)",
    ),
    env_path: Optional[Path] = typer.Option(
        Path.home() / ".pyhub.env",
        "--env-file",
        help="환경 변수 파일(.env) 경로 (디폴트: ~/.pyhub.env)",
    ),
    mcp_method_name: str = "call_tool",
):
    """지정 Tool 호출"""

    log_level = logging.DEBUG if is_verbose else logging.INFO
    init(debug=True, log_level=log_level, toml_path=toml_path, env_path=env_path)

    async_method = getattr(mcp, mcp_method_name, None)
    if async_method is None:
        console.print(f"method not found : {async_method}")
        raise typer.Exit(code=1)

    arguments = {}
    if tool_args:
        for arg in tool_args:
            try:
                key, value = arg.split("=", 1)
                # Attempt to parse value as JSON (handles numbers, booleans, strings)
                try:
                    arguments[key] = json_loads(value)
                except JSONDecodeError:
                    # Fallback to string if not valid JSON
                    arguments[key] = value
            except ValueError:
                console.print(f"[bold red]Error:[/bold red] Invalid argument format: '{arg}'. Use key=value.")
                raise typer.Exit(code=1)

    console.print(f"Calling tool '{tool_name}' with arguments: {arguments}")

    try:
        result = async_to_sync(async_method)(tool_name, arguments=arguments)
        # TODO: 타입에 맞춰 출력 포맷 조절
        console.print(result)
    except ValidationError as e:
        # Catch the ValidationError and print a user-friendly message
        console.print(f"[bold red]Error calling tool '{tool_name}':[/bold red]\n{e}")
        raise typer.Exit(code=1)
    except Exception as e:
        # Catch other potential errors from mcp.call_tool
        console.print(f"[bold red]An unexpected error occurred:[/bold red] {e}")
        # Optionally print traceback if verbose
        if is_verbose:
            console.print_exception(show_locals=True)
        raise typer.Exit(code=1)


@app.command()
def read_resource(
    uri: str = typer.Argument(..., help="resource uri"),
    is_verbose: bool = typer.Option(False, "--verbose"),
    toml_path: Optional[Path] = typer.Option(
        Path.home() / ".pyhub.toml",
        "--toml-file",
        help="toml 설정 파일 경로 (디폴트: ~/.pyhub.toml)",
    ),
    env_path: Optional[Path] = typer.Option(
        Path.home() / ".pyhub.env",
        "--env-file",
        help="환경 변수 파일(.env) 경로 (디폴트: ~/.pyhub.env)",
    ),
):
    """지정 Resource 조회"""

    log_level = logging.DEBUG if is_verbose else logging.INFO
    init(debug=True, log_level=log_level, toml_path=toml_path, env_path=env_path)

    try:
        # TODO: MCP에서는 ValueError, ResourceError 등의 예외는 어떻게 처리해야하나?
        resources = async_to_sync(mcp.read_resource)(uri)
        # TODO: 타입에 맞춰 출력 포맷 조절
        console.print(resources)
    except Exception as e:  # Catch potential errors from mcp.read_resource
        # TODO: Catch more specific MCP errors if available (e.g., ResourceNotFoundError)
        console.print(f"[bold red]Error reading resource '{uri}':[/bold red] {e}")
        if is_verbose:
            console.print_exception(show_locals=True)
        raise typer.Exit(code=1)


@app.command()
def get_prompt(
    prompt_name: str = typer.Argument(..., help="prompt name"),
    prompt_args: list[str] = typer.Argument(
        None, help="Arguments for the prompt in key=value format (e.g., x=10 y='hello world')"
    ),
    is_verbose: bool = typer.Option(False, "--verbose"),
    toml_path: Optional[Path] = typer.Option(
        Path.home() / ".pyhub.toml",
        "--toml-file",
        help="toml 설정 파일 경로 (디폴트: ~/.pyhub.toml)",
    ),
    env_path: Optional[Path] = typer.Option(
        Path.home() / ".pyhub.env",
        "--env-file",
        help="환경 변수 파일(.env) 경로 (디폴트: ~/.pyhub.env)",
    ),
):
    """지정 프롬프트 조회"""

    call_tool(
        tool_name=prompt_name,
        tool_args=prompt_args,
        is_verbose=is_verbose,
        toml_path=toml_path,
        env_path=env_path,
        mcp_method_name="get_prompt",
    )


def print_as_table(title: str, rows: list[BaseModel]) -> None:
    if len(rows) > 0:
        table = Table(title=f"[bold]{title}[/bold]", title_justify="left")

        row = rows[0]
        row_dict = row.model_dump()
        column_names = row_dict.keys()
        for name in column_names:
            table.add_column(name)

        for row in rows:
            columns = []
            for name in column_names:
                value = getattr(row, name, None)
                if value is None:
                    columns.append(f"{value}")
                else:
                    columns.append(f"[blue bold]{value}[/blue bold]")
            table.add_row(*columns)

        console.print(table)

    else:
        console.print(f"[gray]{title} is empty.[/gray]")
