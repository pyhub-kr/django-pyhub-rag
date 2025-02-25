import importlib
import json
import os

from django.apps import apps
from django.core.management.base import BaseCommand, CommandError
from django.db import connections, router


class Command(BaseCommand):
    help = "Load data from a JSONL file into a specified document model"

    def add_arguments(self, parser):
        parser.add_argument("model_path", type=str, help="Path to the document model (e.g., app.FairTradeLawDocument)")
        parser.add_argument("jsonl_path", type=str, help="Path to the JSONL file")

    def handle(self, *args, **options):
        model_path = options["model_path"]
        jsonl_path = options["jsonl_path"]

        # Validate JSONL file exists
        if not os.path.exists(jsonl_path):
            raise CommandError(f"JSONL file does not exist: {jsonl_path}")

        # Import the model
        try:
            app_label, model_name = model_path.split(".")
            model = apps.get_model(app_label, model_name)
        except (ValueError, LookupError) as e:
            try:
                # Try to import as a full module path
                module_path, model_name = model_path.rsplit(".", 1)
                module = importlib.import_module(module_path)
                model = getattr(module, model_name)
            except (ImportError, AttributeError, ValueError) as e:
                raise CommandError(f"Could not import model: {model_path}. Error: {e}")

        # Read JSONL file
        instances = []
        try:
            with open(jsonl_path, "r", encoding="utf-8") as file:
                for line_number, line in enumerate(file, 1):
                    try:
                        data = json.loads(line.strip())
                        instances.append(model(**data))
                    except json.JSONDecodeError:
                        self.stderr.write(self.style.WARNING(f"Invalid JSON at line {line_number}, skipping"))
                    except Exception as e:
                        self.stderr.write(self.style.WARNING(f"Error processing line {line_number}: {e}, skipping"))
        except Exception as e:
            raise CommandError(f"Error reading JSONL file: {e}")

        if not instances:
            self.stdout.write(self.style.WARNING("No valid data found in the JSONL file"))
            return

        # For SQLite, set IDs manually.
        # 올바른 DB 연결을 위해 router를 사용하여 write 위한 데이터베이스를 지정받는다.
        db_write_alias = router.db_for_write(model)
        db_connection = connections[db_write_alias]
        # 현재 sqlite-vec 확장에서는 pk id 자동 생성이 안되므로 수동으로 설정해줘야 한다.
        is_sqlite = db_connection.vendor == "sqlite"
        if is_sqlite:
            try:
                # Get the last ID from the correct database using using()
                last_instance = model.objects.using(db_write_alias).order_by("-id").first()
                last_id = last_instance.id if last_instance else 0

                # Assign incremental IDs
                for i, instance in enumerate(instances):
                    instance.id = last_id + i + 1
            except Exception as e:
                self.stderr.write(self.style.WARNING(f"Could not set IDs for SQLite: {e}"))

        # Bulk create instances
        try:
            created = model.objects.using(db_write_alias).bulk_create(instances)
            self.stdout.write(self.style.SUCCESS(f"Successfully created {len(created)} instances"))
        except Exception as e:
            raise CommandError(f"Error creating instances: {e}")
