import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from django.db import connection
from test_app.models import TestDocument

pytestmark = [
    pytest.mark.django_db,
    pytest.mark.skipif(
        not connection.vendor == "postgresql",
        reason="PostgreSQL database is not available; skipping tests.",
    ),
    pytest.mark.skipif(
        os.environ.get("SKIP_DATABASE_TESTS") is not None,
        reason="Skipping database tests because SKIP_DATABASE_TESTS environment variable is set.",
    ),
]


@pytest.fixture
def sample_text():
    return "This is a test document"


@pytest.fixture
def mock_embedding():
    return [0.1] * 1536  # 1536 dimensions


@patch("openai.Client")
def test_document_creation(mock_client, sample_text, mock_embedding):
    # Mock the OpenAI embedding response
    mock_response = MagicMock()
    mock_response.data = [MagicMock(embedding=mock_embedding)]
    mock_client.return_value.embeddings.create.return_value = mock_response

    doc = TestDocument.objects.create(
        page_content=sample_text,
        metadata={"source": "test"},
    )

    assert doc.page_content == sample_text
    assert doc.metadata["source"] == "test"
    assert len(doc.embedding) == 1536


@patch("openai.Client")
def test_document_update(mock_client, sample_text, mock_embedding):
    # Mock the OpenAI embedding response
    mock_response = MagicMock()
    mock_response.data = [MagicMock(embedding=mock_embedding)]
    mock_client.return_value.embeddings.create.return_value = mock_response

    doc = TestDocument.objects.create(page_content=sample_text)

    new_text = "Updated content"
    doc.page_content = new_text
    doc.save()

    assert doc.page_content == new_text
    mock_client.return_value.embeddings.create.assert_called()


@patch("openai.Client")
def test_bulk_create(mock_client, mock_embedding):
    # Mock the OpenAI embedding response
    mock_response = MagicMock()
    mock_response.data = [MagicMock(embedding=mock_embedding) for _ in range(3)]
    mock_client.return_value.embeddings.create.return_value = mock_response

    docs = [TestDocument(page_content=f"Document {i}") for i in range(3)]

    created_docs = TestDocument.objects.bulk_create(docs)
    assert len(created_docs) == 3
    assert all(doc.embedding is not None for doc in created_docs)


@patch("openai.AsyncClient")
@pytest.mark.asyncio
async def test_document_search(mock_client, mock_embedding):
    # AsyncMock으로 await 가능한 객체를 설정합니다.
    mock_response = MagicMock()
    mock_response.data = [MagicMock(embedding=mock_embedding)]
    mock_client.return_value.embeddings.create = AsyncMock(return_value=mock_response)

    # 테스트용 문서 생성
    for i in range(3):
        await TestDocument.objects.acreate(
            page_content=f"Document {i}",
            embedding=mock_embedding,
        )

    # 유사 문서를 검색
    results = await TestDocument.objects.search("test query", k=2)

    assert len(results) == 2
    assert all(isinstance(doc, TestDocument) for doc in results)


def test_token_size_calculation():
    text = "This is a test"
    token_size = TestDocument.get_token_size(text)
    assert isinstance(token_size, int)
    assert token_size > 0
