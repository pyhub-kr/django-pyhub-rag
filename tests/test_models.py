import os
from typing import Type, cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from django.db import connection
from test_app import models

from pyhub.rag.fields import BaseVectorField
from pyhub.rag.models import AbstractDocument

pytestmark = [
    pytest.mark.django_db,
    pytest.mark.skipif(
        os.environ.get("SKIP_DATABASE_TESTS") is not None,
        reason="Skipping database tests because SKIP_DATABASE_TESTS environment variable is set.",
    ),
]


def mock_embedding_response(dimensions: int, count: int = 1):
    embedding = [0.1] * dimensions

    mock_response = MagicMock()
    mock_response.data = [MagicMock(embedding=embedding)] * count
    return mock_response


@pytest.mark.parametrize(
    "document_model,database_vendor",
    [
        (models.TestPGVectorDocument1536, "postgresql"),
        (models.TestPGVectorDocument3072, "postgresql"),
        (models.TestSQLiteVectorDocument1536, "sqlite"),
        (models.TestSQLiteVectorDocument3072, "sqlite"),
    ],
)
class TestDocumentModels:
    """
    Document 생성 및 관리 기능 테스트

    클래스 레벨 parametrize를 통해 두 가지 문서 모델에 대해 모든 테스트를 실행합니다.
    """

    @pytest.fixture(autouse=True)
    def setup(self, document_model: Type[AbstractDocument], database_vendor):
        """
        테스트에 필요한 기본 데이터를 설정합니다.

        Args:
            document_model: 테스트할 문서 모델 클래스
            database_vendor: DocumentModel 클래스에 지정된 데이터베이스 벤더
        """

        if database_vendor and database_vendor != connection.vendor:
            pytest.skip(f"Skipping test for {database_vendor} database")

        else:
            self.document_model = document_model
            embedding_field = cast(BaseVectorField, document_model._meta.get_field("embedding"))
            self.dimensions = embedding_field.dimensions
            self.sample_text = "This is a test document"

    def _create_mock_embedding(self, mock_client, count: int = 1):
        """
        임베딩 응답을 모의하는 헬퍼 메서드입니다.
        """
        response = mock_embedding_response(self.dimensions, count=count)
        mock_client.return_value.embeddings.create.return_value = response
        return response

    @pytest.mark.it("모의(OpenAI Mock) Client를 사용하여 문서 생성 시 올바른 필드 값이 설정되는지 테스트합니다.")
    @patch("openai.Client")
    def test_document_creation(self, mock_client):
        self._create_mock_embedding(mock_client)

        metadata = {"source": "test"}

        doc = self.document_model.objects.create(
            page_content=self.sample_text,
            metadata=metadata,
        )

        assert doc.page_content == self.sample_text
        assert doc.metadata == metadata
        assert len(doc.embedding) == self.dimensions

    # @pytest.mark.it("문서 업데이트 시 embedding이 재계산되고 OpenAI API 호출이 발생하는지 테스트합니다.")
    # @patch("openai.Client")
    # def test_document_update(self, mock_client):
    #     self._create_mock_embedding(mock_client)
    #     doc = self.document_model.objects.create(id=1, page_content=self.sample_text)
    #
    #     new_text = "Updated content"
    #     doc.page_content = new_text
    #     doc.save()
    #
    #     assert doc.page_content == new_text
    #     mock_client.return_value.embeddings.create.assert_called()

    @pytest.mark.it("여러 문서를 bulk create할 때 모든 문서에 embedding 필드가 null이 아닌지 테스트합니다.")
    @patch("openai.Client")
    def test_bulk_create(self, mock_client):
        count = 3
        self._create_mock_embedding(mock_client, count=count)
        docs = [self.document_model(id=i, page_content=f"Document {i}") for i in range(1, 1 + count)]

        created_docs = self.document_model.objects.bulk_create(docs)

        assert len(created_docs) == 3
        for doc in created_docs:
            assert doc.embedding is not None
            assert len(doc.embedding) == self.dimensions

    @pytest.mark.it("동기(OpenAI Mock) Client를 사용하여 문서 검색 기능이 올바르게 작동하는지 테스트합니다.")
    @patch("openai.Client")
    def test_document_search(self, mock_client):
        count = 3
        self._create_mock_embedding(mock_client)

        # 테스트용 문서 생성
        for i in range(1, count + 1):
            self.document_model.objects.create(
                page_content=f"Document {i}",
                embedding=[0.1] * self.dimensions,
            )

        # 유사 문서를 검색
        results = self.document_model.objects.similarity_search("test query", k=2)

        assert len(results) == 2
        assert all(isinstance(doc, self.document_model) for doc in results)

    @pytest.mark.it("비동기(OpenAI Mock) Client를 사용하여 문서 검색 기능이 올바르게 작동하는지 테스트합니다.")
    @patch("openai.AsyncClient")
    @pytest.mark.asyncio
    async def test_document_asearch(self, mock_client):
        count = 3
        response = mock_embedding_response(self.dimensions, count=count)
        mock_client.return_value.embeddings.create = AsyncMock(return_value=response)

        # 테스트용 문서 생성
        for i in range(1, count + 1):
            await self.document_model.objects.acreate(
                page_content=f"Document {i}",
                embedding=[0.1] * self.dimensions,
            )

        # 유사 문서를 검색
        results = await self.document_model.objects.similarity_search_async("test query", k=2)

        assert len(results) == 2
        assert all(isinstance(doc, self.document_model) for doc in results)

    @pytest.mark.it("문자열의 토큰 수를 올바르게 계산하는지 테스트합니다.")
    def test_token_size_calculation(self):
        text = "This is a test"
        token_size = self.document_model.get_token_size(text)
        assert isinstance(token_size, int)
        assert token_size > 0
