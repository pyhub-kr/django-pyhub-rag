from pathlib import Path
from typing import Dict, List, Optional, Set

import typer
from rich.console import Console

from pyhub.llm import LLM
from pyhub.llm.enum import LLMEmbeddingModelEnum
from pyhub.llm.types import Usage
from pyhub.rag.json import JSONDecodeError, json_dumps, json_loads

app = typer.Typer(name="embed", help="Commands related to embedding")
console = Console()


def validate_embeddings(data: List[Dict]) -> Optional[int]:
    """Validates the dimensions of embedding fields and returns the consistent dimension."""
    dimensions: Set[int] = set()

    for item in data:
        if "embedding" in item and item["embedding"]:
            dimensions.add(len(item["embedding"]))

    if len(dimensions) > 1:
        typer.echo(f"Error: Inconsistent embedding dimensions found: {dimensions}")
        raise typer.Exit(1)

    return dimensions.pop() if dimensions else None


@app.command()
def fill_jsonl(
    jsonl_path: Path = typer.Argument(..., help="Path to the source JSONL file"),
    embedding_model: LLMEmbeddingModelEnum = LLMEmbeddingModelEnum.TEXT_EMBEDDING_3_SMALL,
):
    """Embeds the page_content field values from the JSONL file data and stores them in the embedding field."""

    jsonl_out_path = jsonl_path.with_name(f"{jsonl_path.stem}-out{jsonl_path.suffix}")
    if jsonl_out_path.exists():
        console.print(f"[red]Error: Output file {jsonl_out_path} already exists. Cannot proceed.[/red]")
        raise typer.Exit(1)

    llm = LLM.create(embedding_model.value)
    console.print(f"Using {llm.embedding_model} (dimensions: {llm.get_embed_size()})")
    console.print(f"Parsing {jsonl_path} ...")
    total_usage = Usage()
    try:
        with jsonl_out_path.open("w", encoding="utf-8") as out_f:
            with jsonl_path.open("r", encoding="utf-8") as in_f:
                lines = tuple(in_f)
                total_lines = len(lines)

                for i, line in enumerate(lines):
                    obj = json_loads(line.strip())

                    # Skip if page_content field doesn't exist
                    if "page_content" not in obj:
                        continue

                    # Create embedding field if it doesn't exist
                    embedding = obj.get("embedding")
                    if not embedding:
                        embedding = llm.embed(obj["page_content"])
                        obj["embedding"] = embedding
                        usage = embedding.usage
                        total_usage += usage

                    out_f.write(json_dumps(obj, ensure_ascii=False) + "\n")

                    # Display progress on a single line
                    progress = (i + 1) / total_lines * 100
                    console.print(
                        f"Progress: {progress:.1f}% ({i+1}/{total_lines}) - tokens: {total_usage.input}",
                        end="\r",
                    )

        # Display completion message
        console.print("\n")
        console.print("[green]Embedding completed![/green]")
        console.print(f"Output file created: {jsonl_out_path}")
        console.print(f"Total items: {total_lines}")
        console.print(f"Total tokens: {total_usage.input}")
    except (IOError, JSONDecodeError) as e:
        console.print(f"[red]Error reading file: {e}[/red]")
        raise typer.Exit(1)
