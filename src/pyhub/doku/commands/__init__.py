import logging
from pathlib import Path
from time import sleep
from typing import Optional

import typer
from django.db import transaction
from rich.console import Console

from pyhub import init, print_for_main

app = typer.Typer()
console = Console()


logo = """
    ██████╗ ██╗   ██ ██╗  ██╗ ██╗   ██╗ ██████╗     ██████╗   ██████╗  ██╗  ██╗ ██╗   ██╗
    ██╔══██╗╚██╗ ██╔ ██║  ██║ ██║   ██║ ██╔══██╗    ██╔══██╗ ██╔═══██╗ ██║ ██╔╝ ██║   ██║
    ██████╔╝ ╚████╔╝ ███████║ ██║   ██║ ██████╔╝    ██║  ██║ ██║   ██║ █████╔╝  ██║   ██║
    ██╔═══╝   ╚██╔╝  ██╔══██║ ██║   ██║ ██╔══██╗    ██║  ██║ ██║   ██║ ██╔═██╗  ██║   ██║
    ██║        ██║   ██║  ██║ ╚██████╔╝ ██████╔╝    ██████╔╝ ╚██████╔╝ ██║  ██╗ ╚██████╔╝
    ╚═╝        ╚═╝   ╚═╝  ╚═╝  ╚═════╝  ╚═════╝     ╚═════╝   ╚═════╝  ╚═╝  ╚═╝  ╚═════╝  
"""

app.callback(invoke_without_command=True)(print_for_main(logo))


@app.command()
def run_document_parse_job(
    is_once: bool = typer.Option(False, "--once", help="1회 실행 여부"),
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
    is_verbose: bool = typer.Option(False, "--verbose", help="상세한 처리 정보 표시"),
    is_debug: bool = typer.Option(False, "--debug"),
):
    log_level = logging.DEBUG if is_verbose else logging.INFO
    init(debug=True, log_level=log_level, toml_path=toml_path, env_path=env_path)

    from pyhub.doku import tasks
    from pyhub.doku.models import DocumentParseJob

    def run():
        job_pk: Optional[int] = None

        with transaction.atomic():
            job_qs = DocumentParseJob.objects.pending()
            # 잠긴 행들을 무시하고 당장 잠글 수 있는 행들만 조회
            # 여러 워커가 동시에 실행될 때 효율적인 작업 분배가 가능
            job_qs = job_qs.select_for_update(skip_locked=True)

            job = job_qs.first()

            if job is not None:
                job.processing()
                job_pk = job.pk

        if job_pk is not None:
            if is_verbose:
                console.print(f"Parsing job#{job_pk}")
            tasks.run_document_parse_job(job_pk)
        else:
            if is_verbose:
                console.print("No job to parse")

    try:
        if is_once:
            run()
        else:
            while True:
                run()
                sleep(5)
    except Exception as e:
        console.print(f"[red]{e}[/red]")

        if is_debug:
            console.print_exception()

        raise typer.Exit(code=1)
