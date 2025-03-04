import sys

import typer
from rich.console import Console

from pyhub.llm import LLM
from pyhub.llm.enum import LLMChatModelEnum

# from . import embed, sqlite_vec

app = typer.Typer()
console = Console()

# app.add_typer(embed.app)
# app.add_typer(sqlite_vec.app)


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """PyHub RAG CLI tool"""
    if ctx.invoked_subcommand is None:
        console.print(
            """
        ██████╗ ██╗   ██╗██╗  ██╗██╗   ██╗██████╗     ██╗     ██╗     ███╗   ███╗
        ██╔══██╗╚██╗ ██╔╝██║  ██║██║   ██║██╔══██╗    ██║     ██║     ████╗ ████║
        ██████╔╝ ╚████╔╝ ███████║██║   ██║██████╔╝    ██║     ██║     ██╔████╔██║
        ██╔═══╝   ╚██╔╝  ██╔══██║██║   ██║██╔══██╗    ██║     ██║     ██║╚██╔╝██║
        ██║        ██║   ██║  ██║╚██████╔╝██████╔╝    ███████╗███████╗██║ ╚═╝ ██║
        ╚═╝        ╚═╝   ╚═╝  ╚═╝ ╚═════╝ ╚═════╝     ╚══════╝╚══════╝╚═╝     ╚═╝
        """,
            style="bold blue",
        )
        console.print("Welcome to PyHub RAG CLI!", style="green")


@app.command()
def reply(
    embedding_model: LLMChatModelEnum = LLMChatModelEnum.GPT_4O,
    query: str = typer.Argument(default=None, help="Text to search for similar documents"),
    system_prompt: str = typer.Option(None, help="System prompt to use for the LLM"),
    system_prompt_path: typer.FileText = typer.Option(
        "system_prompt.txt",
        help="Path to a file containing the system prompt",
        exists=False,
    ),
    temperature: float = typer.Option(0.2, help="Temperature for the LLM response (0.0-2.0)"),
    max_tokens: int = typer.Option(1000, help="Maximum number of tokens in the response"),
):
    # Use stdin if available and no query argument was provided
    if query is None and not sys.stdin.isatty():
        query = sys.stdin.read().strip()
    elif query is None:
        console.print("Error: No query provided. Please provide a query or pipe content.", style="red")
        raise typer.Exit(code=1)

    # Handle system prompt options
    if system_prompt_path:
        system_prompt = system_prompt_path.read().strip()

    if system_prompt:
        console.print(f"# System prompt\n\n{system_prompt}\n\n----\n\n", style="blue")

    llm = LLM.create(
        embedding_model.value,
        system_prompt=system_prompt,
        temperature=temperature,
        max_tokens=max_tokens,
    )

    for chunk in llm.reply(query, stream=True):
        console.print(chunk.text, end="")
    console.print()
