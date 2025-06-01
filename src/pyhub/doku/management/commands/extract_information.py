"""Django management command for information extraction."""

import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from pyhub.doku.models import Document, ExtractedInformation
from pyhub.parser.upstage.extractor import (
    ExtractionSchema,
    UpstageInformationExtractor,
)


class Command(BaseCommand):
    help = "Extract structured information from documents using Upstage Information Extract API"

    def add_arguments(self, parser):
        parser.add_argument(
            "--document-id",
            type=int,
            help="Document ID to extract from",
        )
        parser.add_argument(
            "--schema-file",
            type=str,
            help="Path to JSON schema file",
        )
        parser.add_argument(
            "--keys",
            type=str,
            help="Comma-separated list of keys to extract",
        )
        parser.add_argument(
            "--schema-name",
            type=str,
            default="",
            help="Name for this extraction schema",
        )
        parser.add_argument(
            "--extraction-type",
            type=str,
            default="universal",
            choices=["universal", "prebuilt"],
            help="Extraction type",
        )
        parser.add_argument(
            "--document-type",
            type=str,
            help="Document type for prebuilt extraction",
        )
        parser.add_argument(
            "--all-pending",
            action="store_true",
            help="Process all documents without extraction",
        )

    def handle(self, *args, **options):
        # Get documents to process
        if options["all_pending"]:
            documents = Document.objects.filter(
                status=Document.Status.COMPLETED, extracted_information_set__isnull=True
            )
            self.stdout.write(f"Found {documents.count()} documents to process")
        elif options["document_id"]:
            try:
                documents = [Document.objects.get(pk=options["document_id"])]
            except Document.DoesNotExist:
                raise CommandError(f"Document with ID {options['document_id']} not found")
        else:
            raise CommandError("Either --document-id or --all-pending must be specified")

        # Prepare schema
        schema = None
        if options["schema_file"]:
            schema_path = Path(options["schema_file"])
            if not schema_path.exists():
                raise CommandError(f"Schema file not found: {schema_path}")
            schema = ExtractionSchema.from_json_file(schema_path)

        # Parse keys
        keys = None
        if options["keys"]:
            keys = [k.strip() for k in options["keys"].split(",")]

        # Validate extraction parameters
        if options["extraction_type"] == "universal" and not (schema or keys):
            raise CommandError("Universal extraction requires --schema-file or --keys")

        if options["extraction_type"] == "prebuilt" and not options["document_type"]:
            raise CommandError("Prebuilt extraction requires --document-type")

        # Get API key
        import os

        api_key = os.environ.get("UPSTAGE_API_KEY")
        if not api_key:
            raise CommandError("UPSTAGE_API_KEY environment variable not set")

        # Create extractor
        extractor = UpstageInformationExtractor(
            api_key=api_key,
            extraction_type=options["extraction_type"],
            verbose=options["verbosity"] > 1,
        )

        # Process documents
        success_count = 0
        error_count = 0

        for document in documents:
            self.stdout.write(f"Processing: {document.name}")

            try:
                with transaction.atomic():
                    # Extract information
                    with document.file.open("rb") as f:
                        from django.core.files import File

                        django_file = File(f, name=document.file.name)

                        result = extractor.extract_sync(
                            django_file,
                            schema=schema,
                            keys=keys,
                            document_type=options["document_type"],
                        )

                    # Save to database
                    ExtractedInformation.objects.create(
                        document=document,
                        schema_name=options["schema_name"] or "default",
                        extraction_type=options["extraction_type"],
                        document_type=options["document_type"],
                        extracted_data=result,
                        extraction_model=extractor.model,
                    )

                    success_count += 1
                    self.stdout.write(self.style.SUCCESS(f"✓ Extracted from {document.name}"))

                    if options["verbosity"] > 1:
                        self.stdout.write(json.dumps(result, indent=2, ensure_ascii=False))

            except Exception as e:
                error_count += 1
                self.stdout.write(self.style.ERROR(f"✗ Failed to extract from {document.name}: {e}"))

                # Save error to database
                ExtractedInformation.objects.create(
                    document=document,
                    schema_name=options["schema_name"] or "default",
                    extraction_type=options["extraction_type"],
                    document_type=options["document_type"],
                    extracted_data={},
                    error_message=str(e),
                )

        # Summary
        self.stdout.write(self.style.SUCCESS(f"\nCompleted: {success_count} success, {error_count} errors"))
