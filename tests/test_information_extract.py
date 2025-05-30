"""Tests for Information Extract functionality."""

import json
import pytest
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch

from django.core.files import File

from pyhub.parser.upstage.extractor import (
    UpstageInformationExtractor,
    ExtractionSchema,
    BatchInformationExtractor,
)


class TestExtractionSchema:
    """Test ExtractionSchema class."""
    
    def test_from_keys(self):
        """Test creating schema from key list."""
        keys = ["invoice_date", "total_amount", "vendor_name"]
        schema = ExtractionSchema.from_keys(keys)
        
        assert "invoice_date" in schema.fields
        assert "total_amount" in schema.fields
        assert "vendor_name" in schema.fields
        
        # Check field structure
        assert schema.fields["invoice_date"]["type"] == "string"
        assert "description" in schema.fields["invoice_date"]
    
    def test_from_json_file(self):
        """Test loading schema from JSON file."""
        # Create temporary JSON file
        import tempfile
        schema_data = {
            "document_info": {
                "doc_number": {"type": "string"},
                "date": {"type": "string", "format": "date"}
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(schema_data, f)
            temp_path = f.name
        
        try:
            schema = ExtractionSchema.from_json_file(Path(temp_path))
            assert schema.fields == schema_data
        finally:
            Path(temp_path).unlink()


class TestUpstageInformationExtractor:
    """Test UpstageInformationExtractor class."""
    
    def setup_method(self):
        self.api_key = "up_test_key"
        self.extractor = UpstageInformationExtractor(
            api_key=self.api_key,
            extraction_type="universal"
        )
    
    def test_initialization(self):
        """Test extractor initialization."""
        assert self.extractor.api_key == self.api_key
        assert self.extractor.extraction_type == "universal"
        assert self.extractor.model == "universal-extraction"
        
        # Test prebuilt type
        prebuilt_extractor = UpstageInformationExtractor(
            api_key=self.api_key,
            extraction_type="prebuilt"
        )
        assert prebuilt_extractor.model == "prebuilt-extraction"
    
    @patch('pyhub.parser.upstage.extractor.validate_upstage_document')
    @patch('pyhub.parser.upstage.extractor.cached_http_async')
    async def test_extract_with_schema(self, mock_http, mock_validate):
        """Test extraction with schema."""
        # Mock validation to pass
        mock_validate.return_value = None
        
        # Mock response
        mock_http.return_value = {
            "data": {
                "invoice_date": "2024-01-15",
                "total_amount": 1000.0,
                "vendor_name": "Test Vendor"
            }
        }
        
        # Create mock file
        mock_file = Mock(spec=File)
        mock_file.name = "test.pdf"
        mock_file.read.return_value = b"test content"
        mock_file.seek.return_value = None
        
        # Create schema
        schema = ExtractionSchema.from_keys(["invoice_date", "total_amount", "vendor_name"])
        
        # Perform extraction
        result = await self.extractor.extract(mock_file, schema=schema)
        
        # Verify result
        assert result["invoice_date"] == "2024-01-15"
        assert result["total_amount"] == 1000.0
        assert result["vendor_name"] == "Test Vendor"
        
        # Verify API call
        mock_http.assert_called_once()
        call_kwargs = mock_http.call_args[1]
        assert "schema" in call_kwargs["data"]
    
    def test_extract_sync(self):
        """Test synchronous extraction."""
        mock_async_result = AsyncMock(return_value={"test": "data"})
        with patch.object(self.extractor, 'extract', mock_async_result):
            mock_file = Mock(spec=File)
            result = self.extractor.extract_sync(mock_file, keys=["test"])
            
            assert result == {"test": "data"}
            mock_async_result.assert_called_once()


@pytest.mark.asyncio
class TestBatchInformationExtractor:
    """Test batch extraction functionality."""
    
    async def test_batch_extraction(self):
        """Test extracting from multiple files."""
        extractor = BatchInformationExtractor(
            api_key="up_test_key",
            extraction_type="universal"
        )
        
        # Mock files
        files = []
        for i in range(3):
            mock_file = Mock(spec=File)
            mock_file.name = f"test{i}.pdf"
            mock_file.read.return_value = b"test content"
            mock_file.seek.return_value = None
            files.append(mock_file)
        
        # Mock extract method
        async def mock_extract(*args, **kwargs):
            file = args[0]
            return {"file": file.name, "data": "extracted"}
        
        with patch.object(extractor, 'extract', side_effect=mock_extract):
            results = await extractor.extract_batch(
                files,
                keys=["test_key"]
            )
            
            assert len(results) == 3
            for i, result in enumerate(results):
                assert "file" in result or "error" in result
                if "file" in result:
                    assert result["file"] == f"test{i}.pdf"
