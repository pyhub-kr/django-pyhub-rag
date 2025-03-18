import sys

import typer
from rich.console import Console

from pyhub.llm import LLM
from pyhub.llm.types import LLMChatModelEnum

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
        console.print("Welcome to PyHub LLM CLI!", style="green")


@app.command()
def ask(
    embedding_model: LLMChatModelEnum = LLMChatModelEnum.GPT_4O,
    query: str = typer.Argument(..., help="Text to search for similar documents"),
    context: str = typer.Option(None, help="Context to provide to the LLM"),
    system_prompt: str = typer.Option(None, help="System prompt to use for the LLM"),
    system_prompt_path: str = typer.Option(
        "system_prompt.txt",
        help="Path to a file containing the system prompt",
    ),
    temperature: float = typer.Option(0.2, help="Temperature for the LLM response (0.0-2.0)"),
    max_tokens: int = typer.Option(1000, help="Maximum number of tokens in the response"),
):
    # Use stdin as context if available and no context argument was provided
    if context is None and not sys.stdin.isatty():
        context = sys.stdin.read().strip()

    # Handle system prompt options
    if system_prompt_path:
        try:
            with open(system_prompt_path, "r") as f:
                system_prompt = f.read().strip()
        except IOError:
            pass

    if context:
        system_prompt = ((system_prompt or "") + "\n\n" + f"<context>{context}</context>").strip()

    # if system_prompt:
    #     console.print(f"# System prompt\n\n{system_prompt}\n\n----\n\n", style="blue")

    llm = LLM.create(
        embedding_model.value,
        system_prompt=system_prompt,
        temperature=temperature,
        max_tokens=max_tokens,
    )

    for chunk in llm.ask(query, stream=True):
        console.print(chunk.text, end="")
    console.print()
