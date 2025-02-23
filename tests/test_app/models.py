from pyhub.rag.fields.postgres import PGVectorField
from pyhub.rag.fields.sqlite import SQLiteVectorField
from pyhub.rag.models.postgres import PostgresDocument
from pyhub.rag.models.sqlite import SQLiteDocument


class TestPostgresDocument1536(PostgresDocument):

    class Meta:
        app_label = "test_app"
        indexes = [
            PostgresDocument.make_hnsw_index(
                "test_document_embedding_idx_1536",
                field_type="vector",
                operator_class="cosine",
            ),
        ]


class TestPostgresDocument3072(PostgresDocument):
    embedding = PGVectorField(dimensions=3072, editable=False)

    class Meta:
        app_label = "test_app"
        indexes = [
            PostgresDocument.make_hnsw_index(
                "test_document_embedding_idx_3072",
                field_type="vector",
                operator_class="cosine",
            ),
        ]


class TestSQLiteDocument1536(SQLiteDocument):
    pass


class TestSQLiteDocument3072(SQLiteDocument):
    embedding = SQLiteVectorField(dimensions=3072, editable=False)
