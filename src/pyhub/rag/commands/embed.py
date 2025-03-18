from pathlib import Path
from typing import Dict, List, Optional, Set

import typer
from rich.console import Console

from pyhub.llm import LLM
from pyhub.llm.types import LLMEmbeddingModelEnum, Usage
from pyhub.rag.json import JSONDecodeError, json_dumps, json_loads

app = typer.Typer(name="embed", help="LLM 임베딩 관련 명령")
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
    jsonl_path: Path = typer.Argument(..., help="소스 JSONL 파일 경로"),
    embedding_model: LLMEmbeddingModelEnum = LLMEmbeddingModelEnum.TEXT_EMBEDDING_3_SMALL,
):
    """JSONL 파일 데이터의 page_content 필드 값을 임베딩하고 embedding 필드에 저장합니다."""

    jsonl_out_path = jsonl_path.with_name(f"{jsonl_path.stem}-out{jsonl_path.suffix}")
    if jsonl_out_path.exists():
        console.print(f"[red]오류: 출력 파일 {jsonl_out_path}이(가) 이미 존재합니다. 진행할 수 없습니다.[/red]")
        raise typer.Exit(1)

    llm = LLM.create(embedding_model.value)
    console.print(f"{llm.embedding_model} 사용 중 (차원: {llm.get_embed_size()})")
    console.print(f"{jsonl_path} 파싱 중 ...")
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

                    out_f.write(json_dumps(obj) + "\n")

                    # Display progress on a single line
                    progress = (i + 1) / total_lines * 100
                    console.print(
                        f"진행률: {progress:.1f}% ({i+1}/{total_lines}) - 토큰: {total_usage.input}",
                        end="\r",
                    )

        # Display completion message
        console.print("\n")
        console.print("[green]임베딩 완료![/green]")
        console.print(f"출력 파일 생성됨: {jsonl_out_path}")
        console.print(f"총 항목 수: {total_lines}")
        console.print(f"총 토큰 수: {total_usage.input}")
    except (IOError, JSONDecodeError) as e:
        console.print(f"[red]파일 읽기 오류: {e}[/red]")
        raise typer.Exit(1)
