from pyhub.rag.fields.postgres import PGVectorField
from pyhub.rag.fields.sqlite import SQLiteVectorField
from pyhub.rag.models.postgres import PGVectorDocument
from pyhub.rag.models.sqlite import SQLiteVectorDocument


class TestPGVectorDocument1536(PGVectorDocument):

    class Meta:
        app_label = "test_app"
        indexes = [
            PGVectorDocument.make_hnsw_index(
                "test_document_embedding_idx_1536",
                field_type="vector",
                operator_class="cosine",
            ),
        ]


class TestPGVectorDocument3072(PGVectorDocument):
    embedding = PGVectorField(
        dimensions=3072,
        editable=False,
        embedding_model="text-embedding-3-large",
    )

    class Meta:
        app_label = "test_app"
        indexes = [
            PGVectorDocument.make_hnsw_index(
                "test_document_embedding_idx_3072",
                field_type="vector",
                operator_class="cosine",
            ),
        ]


class TestSQLiteVectorDocument1536(SQLiteVectorDocument):
    pass


class TestSQLiteVectorDocument3072(SQLiteVectorDocument):
    embedding = SQLiteVectorField(
        dimensions=3072,
        editable=False,
        embedding_model="text-embedding-3-large",
    )
