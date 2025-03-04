import importlib
import json
import os
import tempfile
import urllib.parse
import urllib.request
from typing import Any, Generator
from urllib.error import URLError

from django.apps import apps
from django.core.management.base import BaseCommand, CommandError
from django.db import router


class Command(BaseCommand):
    help = "Load data from a JSONL file into a specified document model"

    def add_arguments(self, parser):
        parser.add_argument("model_path", type=str, help="Path to the document model (e.g., app.FairTradeLawDocument)")
        parser.add_argument("jsonl_path", type=str, help="Path to the JSONL file or URL")
        parser.add_argument("--batch_size", type=int, default=1000, help="Batch size for bulk creation")

    def read_jsonl(self, jsonl_path: str, model) -> Generator[Any, None, None]:
        """JSONL 파일을 한 줄씩 읽어서 모델 인스턴스를 생성하는 제너레이터"""
        try:
            with open(jsonl_path, "r", encoding="utf-8") as file:
                for line_number, line in enumerate(file, 1):
                    try:
                        data = json.loads(line.strip())
                        yield model(**data)
                    except json.JSONDecodeError:
                        self.stderr.write(self.style.WARNING(f"Invalid JSON at line {line_number}, skipping"))
                    except Exception as e:
                        self.stderr.write(self.style.WARNING(f"Error processing line {line_number}: {e}, skipping"))
        except Exception as e:
            raise CommandError(f"Error reading JSONL file: {e}")

    def handle(self, *args, **options):
        model_path = options["model_path"]
        jsonl_path = options["jsonl_path"]
        batch_size = options["batch_size"]

        # Check if jsonl_path is a URL
        is_url = jsonl_path.startswith(("http://", "https://"))
        temp_file = None

        try:
            if is_url:
                self.stdout.write(f"Downloading JSONL from URL: {jsonl_path}")
                try:
                    # Create a temporary file for the downloaded content
                    fd, temp_file = tempfile.mkstemp(suffix=".jsonl")
                    os.close(fd)
                    urllib.request.urlretrieve(jsonl_path, temp_file)
                    jsonl_path = temp_file
                    self.stdout.write(self.style.SUCCESS(f"Downloaded to temporary file: {jsonl_path}"))
                except URLError as e:
                    raise CommandError(f"Failed to download JSONL file: {e}")
            # Validate JSONL file exists
            elif not os.path.exists(jsonl_path):
                raise CommandError(f"JSONL file does not exist: {jsonl_path}")

            # Import the model
            try:
                app_label, model_name = model_path.split(".")
                model = apps.get_model(app_label, model_name)
            except (ValueError, LookupError):
                try:
                    # Try to import as a full module path
                    module_path, model_name = model_path.rsplit(".", 1)
                    module = importlib.import_module(module_path)
                    model = getattr(module, model_name)
                except (ImportError, AttributeError, ValueError) as e:
                    raise CommandError(f"Could not import model: {model_path}. Error: {e}")

            # 올바른 DB 연결을 위해 router를 사용하여 write 위한 데이터베이스를 지정받는다.
            db_write_alias = router.db_for_write(model)

            # 제너레이터를 사용하여 JSONL 파일 읽기 및 배치 단위로 처리
            batch_instances = []
            total_created = 0

            for instance in self.read_jsonl(jsonl_path, model):
                batch_instances.append(instance)

                # 배치 크기에 도달하면 bulk_create 실행
                if len(batch_instances) >= batch_size:
                    try:
                        created = model.objects.using(db_write_alias).bulk_create(
                            batch_instances, batch_size=batch_size
                        )
                        total_created += len(created)
                        self.stdout.write(f"Created batch of {len(created)} instances")
                        batch_instances = []
                    except Exception as e:
                        raise CommandError(f"Error creating instances batch: {e}")

            # 남은 인스턴스 처리
            if batch_instances:
                try:
                    created = model.objects.using(db_write_alias).bulk_create(batch_instances, batch_size=batch_size)
                    total_created += len(created)
                    self.stdout.write(f"Created final batch of {len(created)} instances")
                except Exception as e:
                    raise CommandError(f"Error creating final batch: {e}")

            if total_created == 0:
                self.stdout.write(self.style.WARNING("No valid data found in the JSONL file"))
            else:
                self.stdout.write(self.style.SUCCESS(f"Successfully created {total_created} instances in total"))

        finally:
            # Clean up temporary file if it was created
            if temp_file and os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                    self.stdout.write("Temporary file removed")
                except OSError as e:
                    self.stderr.write(f"Could not remove temporary file: {e}")
