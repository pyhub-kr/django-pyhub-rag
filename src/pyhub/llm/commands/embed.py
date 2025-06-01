import logging
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from pyhub import init
from pyhub.llm import LLM
from pyhub.llm.json import JSONDecodeError, json_dumps, json_loads
from pyhub.llm.types import LLMEmbeddingModelEnum, Usage

app = typer.Typer(
    name="embed",
    help="LLM 임베딩 관련 명령",
    invoke_without_command=True,
)
console = Console()


@app.callback()
def embed_callback(ctx: typer.Context):
    """임베딩 관련 명령어를 제공합니다."""
    if ctx.invoked_subcommand is None:
        # 서브커맨드가 없으면 help 출력
        console.print(ctx.get_help())
        raise typer.Exit()


@app.command()
def fill_jsonl(
    jsonl_path: Path = typer.Argument(..., help="소스 JSONL 파일 경로"),
    jsonl_out_path: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="출력 JSONL 파일 경로 (디폴트: 입력 jsonl 파일 경로에 -out 을 추가한 경로를 사용합니다.)",
    ),
    embedding_model: LLMEmbeddingModelEnum = typer.Option(
        LLMEmbeddingModelEnum.TEXT_EMBEDDING_3_SMALL,
        "--embedding-model",
        "-m",
        help="임베딩 모델",
    ),
    is_force: bool = typer.Option(False, "--force", "-f", help="확인 없이 출력 폴더 삭제 후 재생성"),
    is_verbose: bool = typer.Option(False, "--verbose", help="상세한 처리 정보 표시"),
    enable_cache: bool = typer.Option(
        False,
        "--enable-cache",
        help="API 응답 캐시를 활성화합니다",
    ),
):
    """JSONL 파일 데이터의 page_content 필드 값을 임베딩하고 embedding 필드에 저장합니다."""

    if jsonl_path.suffix.lower() != ".jsonl":
        console.print(f"[red]{jsonl_path} 파일이 jsonl 확장자가 아닙니다.[/red]")
        raise typer.Exit(1)

    # 출력 경로가 지정되지 않은 경우 기존 자동 생성 로직 사용
    if jsonl_out_path is None:
        jsonl_out_path = jsonl_path.with_name(f"{jsonl_path.stem}-out{jsonl_path.suffix}")

    if jsonl_out_path.exists() and not is_force:
        console.print(f"[red]오류: 출력 파일 {jsonl_out_path}이(가) 이미 존재합니다. 진행할 수 없습니다.[/red]")
        raise typer.Exit(1)

    if is_verbose:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO
    init(debug=True, log_level=log_level)

    llm = LLM.create(embedding_model)

    if is_verbose:
        table = Table(show_header=True, header_style="bold blue")
        table.add_column("설정", style="cyan")
        table.add_column("값", style="green")
        table.add_row("임베딩된 jsonl 파일 생성 경로", str(jsonl_out_path))
        table.add_row("임베딩 모델", f"{llm.embedding_model} ({llm.get_embed_size()})")
        console.print(table)

    console.print(f"{jsonl_path} ...")
    total_usage = Usage()

    try:
        with jsonl_out_path.open("wt", encoding="utf-8") as out_f:
            with jsonl_path.open("rt", encoding="utf-8") as in_f:
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
                        embedding = llm.embed(obj["page_content"], enable_cache=enable_cache)
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


@app.command()
def text(
    ctx: typer.Context,
    query: Optional[str] = typer.Argument(None, help="임베딩할 텍스트"),
    embedding_model: LLMEmbeddingModelEnum = typer.Option(
        LLMEmbeddingModelEnum.TEXT_EMBEDDING_3_SMALL,
        "--model",
        "-m",
        help="임베딩 모델",
    ),
    output_format: str = typer.Option(
        "json",
        "--format",
        "-f",
        help="출력 형식 (json, list, numpy)",
    ),
    is_verbose: bool = typer.Option(False, "--verbose", help="상세한 처리 정보 표시"),
    enable_cache: bool = typer.Option(
        False,
        "--enable-cache",
        help="API 응답 캐시를 활성화합니다",
    ),
):
    """텍스트를 임베딩하여 벡터를 출력합니다."""

    # query가 없으면 help 출력
    if query is None:
        console.print(ctx.get_help())
        raise typer.Exit()

    if is_verbose:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO
    init(debug=True, log_level=log_level)

    llm = LLM.create(embedding_model)

    if is_verbose:
        console.print(f"[dim]임베딩 모델: {llm.embedding_model} (차원: {llm.get_embed_size()})[/dim]")
        console.print(f"[dim]입력 텍스트 길이: {len(query)} 문자[/dim]")

    # 임베딩 생성
    embedding_result = llm.embed(query, enable_cache=enable_cache)

    # 출력 형식에 따라 처리
    if output_format == "json":
        output = {
            "text": query,
            "embedding": embedding_result.array,
            "model": str(llm.embedding_model),
            "dimensions": len(embedding_result.array),
            "usage": (
                {
                    "input_tokens": embedding_result.usage.input,
                    "total_tokens": embedding_result.usage.total,
                }
                if embedding_result.usage
                else None
            ),
        }
        console.print(json_dumps(output, indent=2))
    elif output_format == "list":
        console.print(embedding_result.array)
    elif output_format == "numpy":
        console.print(f"array({embedding_result.array})")
    else:
        console.print(f"[red]오류: 지원하지 않는 출력 형식입니다: {output_format}[/red]")
        raise typer.Exit(1)


@app.command()
def similarity(
    ctx: typer.Context,
    text1: Optional[str] = typer.Argument(None, help="첫 번째 텍스트"),
    text2: Optional[str] = typer.Argument(None, help="두 번째 텍스트"),
    vector1_path: Optional[Path] = typer.Option(
        None,
        "--vector1",
        help="첫 번째 벡터 파일 (JSON 형식)",
    ),
    vector2_path: Optional[Path] = typer.Option(
        None,
        "--vector2",
        help="두 번째 벡터 파일 (JSON 형식)",
    ),
    embedding_model: LLMEmbeddingModelEnum = typer.Option(
        LLMEmbeddingModelEnum.TEXT_EMBEDDING_3_SMALL,
        "--model",
        "-m",
        help="임베딩 모델 (텍스트 입력 시)",
    ),
    metric: str = typer.Option(
        "cosine",
        "--metric",
        help="유사도 측정 방식 (cosine, euclidean, dot)",
    ),
    is_verbose: bool = typer.Option(False, "--verbose", help="상세한 처리 정보 표시"),
    enable_cache: bool = typer.Option(
        False,
        "--enable-cache",
        help="API 응답 캐시를 활성화합니다",
    ),
):
    """두 텍스트 또는 벡터 간의 유사도를 계산합니다."""

    # 입력 검증
    if not any([text1, text2, vector1_path, vector2_path]):
        console.print(ctx.get_help())
        raise typer.Exit()

    if (text1 or text2) and (vector1_path or vector2_path):
        console.print("[red]오류: 텍스트와 벡터 파일을 동시에 지정할 수 없습니다.[/red]")
        raise typer.Exit(1)

    if (text1 and not text2) or (text2 and not text1):
        console.print("[red]오류: 두 개의 텍스트를 모두 입력해주세요.[/red]")
        raise typer.Exit(1)

    if (vector1_path and not vector2_path) or (vector2_path and not vector1_path):
        console.print("[red]오류: 두 개의 벡터 파일을 모두 지정해주세요.[/red]")
        raise typer.Exit(1)

    if is_verbose:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO
    init(debug=True, log_level=log_level)

    # 벡터 준비
    import numpy as np

    if text1 and text2:
        # 텍스트를 임베딩으로 변환
        llm = LLM.create(embedding_model)
        if is_verbose:
            console.print(f"[dim]임베딩 모델: {llm.embedding_model}[/dim]")
            console.print(f"[dim]텍스트 1 길이: {len(text1)} 문자[/dim]")
            console.print(f"[dim]텍스트 2 길이: {len(text2)} 문자[/dim]")

        embed1 = llm.embed(text1, enable_cache=enable_cache)
        embed2 = llm.embed(text2, enable_cache=enable_cache)
        vec1 = np.array(embed1.array)
        vec2 = np.array(embed2.array)
    else:
        # 벡터 파일 로드
        try:
            import json

            with vector1_path.open("r") as f:
                data1 = json.load(f)
                vec1 = np.array(data1.get("embedding", data1))

            with vector2_path.open("r") as f:
                data2 = json.load(f)
                vec2 = np.array(data2.get("embedding", data2))

        except Exception as e:
            console.print(f"[red]벡터 파일 로드 오류: {e}[/red]")
            raise typer.Exit(1)

    # 유사도 계산
    if metric == "cosine":
        # 코사인 유사도
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        similarity = dot_product / (norm1 * norm2)
        distance = 1 - similarity
    elif metric == "euclidean":
        # 유클리디안 거리
        distance = np.linalg.norm(vec1 - vec2)
        # 유사도로 변환 (0~1 범위)
        similarity = 1 / (1 + distance)
    elif metric == "dot":
        # 내적
        similarity = np.dot(vec1, vec2)
        distance = -similarity
    else:
        console.print(f"[red]오류: 지원하지 않는 측정 방식입니다: {metric}[/red]")
        raise typer.Exit(1)

    # 결과 출력
    result_table = Table(title="유사도 계산 결과")
    result_table.add_column("측정 방식", style="cyan")
    result_table.add_column("유사도", style="green")
    result_table.add_column("거리", style="yellow")
    result_table.add_row(metric.capitalize(), f"{similarity:.6f}", f"{distance:.6f}")
    console.print(result_table)

    # 해석
    if metric == "cosine":
        if similarity > 0.9:
            interpretation = "매우 유사함"
        elif similarity > 0.7:
            interpretation = "유사함"
        elif similarity > 0.5:
            interpretation = "어느 정도 유사함"
        elif similarity > 0.3:
            interpretation = "약간 유사함"
        else:
            interpretation = "유사하지 않음"
        console.print(f"\n해석: [bold]{interpretation}[/bold]")
        console.print("[dim]코사인 유사도: -1 (정반대) ~ 0 (무관) ~ 1 (동일)[/dim]")


@app.command()
def batch(
    ctx: typer.Context,
    input_file: Optional[Path] = typer.Argument(
        None,
        help="입력 파일 경로 (텍스트 파일, 한 줄에 하나씩)",
    ),
    output_path: Path = typer.Option(
        Path("embeddings.jsonl"),
        "--output",
        "-o",
        help="출력 파일 경로 (JSONL 형식)",
    ),
    embedding_model: LLMEmbeddingModelEnum = typer.Option(
        LLMEmbeddingModelEnum.TEXT_EMBEDDING_3_SMALL,
        "--model",
        "-m",
        help="임베딩 모델",
    ),
    batch_size: int = typer.Option(
        100,
        "--batch-size",
        "-b",
        help="배치 크기",
    ),
    is_force: bool = typer.Option(False, "--force", "-f", help="기존 파일 덮어쓰기"),
    is_verbose: bool = typer.Option(False, "--verbose", help="상세한 처리 정보 표시"),
    enable_cache: bool = typer.Option(
        False,
        "--enable-cache",
        help="API 응답 캐시를 활성화합니다",
    ),
):
    """여러 텍스트를 일괄적으로 임베딩합니다."""

    # 입력 파일 확인
    if not input_file:
        console.print(ctx.get_help())
        raise typer.Exit()

    if not input_file.exists():
        console.print(f"[red]오류: 입력 파일이 존재하지 않습니다: {input_file}[/red]")
        raise typer.Exit(1)

    # 출력 파일 확인
    if output_path.exists() and not is_force:
        console.print(f"[red]오류: 출력 파일이 이미 존재합니다: {output_path}[/red]")
        console.print("[dim]덮어쓰려면 --force 옵션을 사용하세요.[/dim]")
        raise typer.Exit(1)

    if is_verbose:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO
    init(debug=True, log_level=log_level)

    # LLM 생성
    llm = LLM.create(embedding_model)

    if is_verbose:
        console.print(f"[dim]임베딩 모델: {llm.embedding_model} (차원: {llm.get_embed_size()})[/dim]")
        console.print(f"[dim]배치 크기: {batch_size}[/dim]")

    # 텍스트 로드
    try:
        with input_file.open("r", encoding="utf-8") as f:
            texts = [line.strip() for line in f if line.strip()]
    except Exception as e:
        console.print(f"[red]입력 파일 읽기 오류: {e}[/red]")
        raise typer.Exit(1)

    if not texts:
        console.print("[yellow]경고: 입력 파일에 텍스트가 없습니다.[/yellow]")
        raise typer.Exit()

    console.print(f"[blue]총 {len(texts)}개의 텍스트를 처리합니다.[/blue]")

    # 배치 처리
    total_usage = Usage()
    results = []

    import time

    start_time = time.time()

    try:
        with output_path.open("w", encoding="utf-8") as out_f:
            for i in range(0, len(texts), batch_size):
                batch = texts[i : i + batch_size]
                batch_start = time.time()

                # 배치 임베딩 (현재는 개별 처리, 추후 배치 API 지원 시 수정)
                batch_results = []
                batch_usage = Usage()

                for text in batch:
                    embed_result = llm.embed(text, enable_cache=enable_cache)
                    batch_results.append(
                        {
                            "text": text,
                            "embedding": embed_result.array,
                            "model": str(llm.embedding_model),
                        }
                    )
                    if embed_result.usage:
                        batch_usage += embed_result.usage

                # 결과 저장
                for result in batch_results:
                    out_f.write(json_dumps(result) + "\n")
                    results.append(result)

                total_usage += batch_usage
                batch_time = time.time() - batch_start

                # 진행 상황 표시
                progress = min(i + batch_size, len(texts))
                percentage = (progress / len(texts)) * 100
                console.print(
                    f"진행: {percentage:.1f}% ({progress}/{len(texts)}) - "
                    f"배치 시간: {batch_time:.2f}초 - "
                    f"총 토큰: {total_usage.input}",
                    end="\r",
                )

        # 완료
        total_time = time.time() - start_time
        console.print()  # 줄바꿈
        console.print("[green]✓ 임베딩 완료![/green]")

        # 통계
        stats_table = Table(title="처리 통계")
        stats_table.add_column("항목", style="cyan")
        stats_table.add_column("값", style="green")
        stats_table.add_row("처리된 텍스트", str(len(texts)))
        stats_table.add_row("총 입력 토큰", str(total_usage.input))
        stats_table.add_row("처리 시간", f"{total_time:.2f}초")
        stats_table.add_row("평균 처리 속도", f"{len(texts) / total_time:.1f} 텍스트/초")
        stats_table.add_row("출력 파일", str(output_path))
        console.print(stats_table)

    except Exception as e:
        console.print(f"\n[red]처리 중 오류 발생: {e}[/red]")
        raise typer.Exit(1)
