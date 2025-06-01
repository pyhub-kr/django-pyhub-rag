"""Upstage Information Extract API wrapper."""

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
from django.core.files import File

from pyhub.http import cached_http_async

from .settings import DEFAULT_TIMEOUT
from .validators import validate_upstage_document

logger = logging.getLogger(__name__)

# API endpoints
INFORMATION_EXTRACT_API_URL = "https://api.upstage.ai/v1/information-extraction"


@dataclass
class ExtractionSchema:
    """Schema definition for information extraction."""

    fields: Dict[str, Any]

    @classmethod
    def from_json_file(cls, path: Path) -> "ExtractionSchema":
        """Load schema from JSON file."""
        with open(path, "r", encoding="utf-8") as f:
            fields = json.load(f)
        return cls(fields=fields)

    @classmethod
    def from_keys(cls, keys: List[str]) -> "ExtractionSchema":
        """Create simple schema from key list."""
        fields = {key: {"type": "string", "description": f"Extract {key}"} for key in keys}
        return cls(fields=fields)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API request."""
        return self.fields


class UpstageInformationExtractor:
    """Upstage Information Extract API client."""

    def __init__(
        self,
        api_key: str,
        extraction_type: str = "universal",  # universal or prebuilt
        model: Optional[str] = None,
        timeout: int = DEFAULT_TIMEOUT,
        ignore_cache: bool = False,
        verbose: bool = False,
    ):
        self.api_key = api_key
        self.extraction_type = extraction_type
        self.model = model
        self.timeout = timeout
        self.ignore_cache = ignore_cache
        self.verbose = verbose

        # Set default model based on extraction type
        if not self.model:
            self.model = "universal-extraction" if extraction_type == "universal" else "prebuilt-extraction"

    def is_valid(self, file: File, raise_exception: bool = True) -> bool:
        """Validate input file."""
        return validate_upstage_document(file, raise_exception=raise_exception)

    async def extract(
        self,
        file: File,
        schema: Optional[ExtractionSchema] = None,
        keys: Optional[List[str]] = None,
        document_type: Optional[str] = None,  # For prebuilt models
    ) -> Dict[str, Any]:
        """
        Extract information from document.

        Args:
            file: Input document file
            schema: Extraction schema (for universal extraction)
            keys: Simple key list (alternative to schema)
            document_type: Document type for prebuilt models (invoice, receipt, etc.)

        Returns:
            Extracted information as dictionary
        """
        # Validate file
        self.is_valid(file, raise_exception=True)

        # Prepare request data
        headers = {
            "Authorization": f"Bearer {self.api_key}",
        }

        # Reset file position
        file.seek(0)

        files = {
            "document": (file.name, file.read(), "application/octet-stream"),
        }

        data = {
            "model": self.model,
            "extraction_type": self.extraction_type,
        }

        # Add schema or keys for universal extraction
        if self.extraction_type == "universal":
            if schema:
                data["schema"] = json.dumps(schema.to_dict())
            elif keys:
                # Convert keys to simple schema
                simple_schema = ExtractionSchema.from_keys(keys)
                data["schema"] = json.dumps(simple_schema.to_dict())
            else:
                raise ValueError("Either schema or keys must be provided for universal extraction")

        # Add document type for prebuilt extraction
        elif self.extraction_type == "prebuilt":
            if not document_type:
                raise ValueError("document_type must be provided for prebuilt extraction")
            data["document_type"] = document_type

        # Log request details if verbose
        if self.verbose:
            logger.info(f"Extracting from {file.name} using {self.extraction_type} extraction")
            if schema or keys:
                logger.info(f"Schema/Keys: {data.get('schema', 'N/A')}")

        # Make API request
        try:
            response_data = await cached_http_async(
                "POST",
                INFORMATION_EXTRACT_API_URL,
                headers=headers,
                files=files,
                data=data,
                timeout=self.timeout,
                ignore_cache=self.ignore_cache,
                cache_namespace="upstage_information_extract",
                cache_params={
                    "model": self.model,
                    "extraction_type": self.extraction_type,
                    "schema": data.get("schema"),
                    "document_type": data.get("document_type"),
                },
            )

            # Parse response
            if "error" in response_data:
                raise Exception(f"API Error: {response_data['error']}")

            # Extract results
            extracted_data = response_data.get("data", {})

            if self.verbose:
                logger.info(f"Successfully extracted {len(extracted_data)} fields")

            return extracted_data

        except httpx.TimeoutException:
            raise Exception(f"Request timeout after {self.timeout} seconds")
        except Exception as e:
            logger.error(f"Extraction failed: {str(e)}")
            raise

    def extract_sync(
        self,
        file: File,
        schema: Optional[ExtractionSchema] = None,
        keys: Optional[List[str]] = None,
        document_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Synchronous version of extract."""
        import asyncio

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self.extract(file, schema, keys, document_type))
        finally:
            loop.close()


class BatchInformationExtractor(UpstageInformationExtractor):
    """Batch processing for multiple documents."""

    async def extract_batch(
        self,
        files: List[File],
        schema: Optional[ExtractionSchema] = None,
        keys: Optional[List[str]] = None,
        document_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Extract information from multiple documents."""
        import asyncio

        tasks = []
        for file in files:
            task = self.extract(file, schema, keys, document_type)
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        extracted_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Failed to extract from {files[i].name}: {result}")
                extracted_results.append({"error": str(result), "file": files[i].name})
            else:
                result["_source_file"] = files[i].name
                extracted_results.append(result)

        return extracted_results
