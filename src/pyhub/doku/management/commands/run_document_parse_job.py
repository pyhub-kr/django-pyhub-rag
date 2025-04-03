from time import sleep
from typing import Optional, Annotated

from django.conf import settings
from django.core.management.base import CommandError
from django.db import transaction
from django_rich.management import RichCommand
from django_typer.management import Typer, TyperCommand
from typer import Option

from pyhub.doku import tasks
from pyhub.doku.models import DocumentParseJob

app = Typer()


# TODO: python manage.py 를 통한 실행에서는 self.console.log 출력에서는 timezone 설정이 먹히지 않고, 시각이 UTC로 출력되는 현상

class Command(RichCommand, TyperCommand):
    def handle(
        self,
        is_once: Annotated[bool, Option("--once", help="1회 실행 여부")] = False,
        is_verbose: Annotated[bool, Option("--verbose", help="상세한 처리 정보 표시 여부")] = False,
    ):
        # TODO: celery 혹은 django-tasks를 통한 요청 분기

        def run():
            job_pk: Optional[int] = None

            with transaction.atomic():
                job_qs = DocumentParseJob.objects.pending()
                # Lock rows to prevent race conditions with multiple workers
                job_qs = job_qs.select_for_update(skip_locked=True)

                job = job_qs.first()

                if job is not None:
                    job.processing()
                    job_pk = job.pk

            if job_pk is not None:
                if is_verbose:
                    self.console.log(f"Parsing job#{job_pk}")
                tasks.run_document_parse_job(job_pk)
            else:
                if is_verbose:
                    self.console.log("No job to parse")

        try:
            if is_once:
                run()
            else:
                while True:
                    run()
                    sleep(5)  # Consider making the sleep interval configurable
        except Exception as e:
            self.console.print(f"[red]Error: {e}[/red]")
            if settings.DEBUG:
                self.console.print_exception(show_locals=True)
            raise CommandError(f"Job execution failed: {e}")