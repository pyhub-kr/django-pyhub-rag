import logging

from django.db import migrations, models
from pgvector.django import HalfVectorField, HnswIndex

from pyhub.db.migrations import CreateModelOnlyPostgres, CreateModelOnlySqlite
from pyhub.rag.fields.postgres import PGVectorField
from pyhub.rag.fields.sqlite import SQLiteVectorField

logger = logging.getLogger(__name__)


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        CreateModelOnlyPostgres(
            name="TestPostgresDocument1536",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("page_content", models.TextField()),
                ("metadata", models.JSONField()),
                ("embedding", PGVectorField(dimensions=1536)),
            ],
            options={
                "indexes": [
                    HnswIndex(
                        name="test_document_embedding_idx_1536",
                        fields=["embedding"],
                        m=16,
                        ef_construction=64,
                        opclasses=["vector_cosine_ops"],
                    ),
                ],
            },
        ),
        CreateModelOnlyPostgres(
            name="TestPostgresDocument3072",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("page_content", models.TextField()),
                ("metadata", models.JSONField()),
                ("embedding", HalfVectorField(dimensions=1536 * 2)),
            ],
            options={
                "indexes": [
                    HnswIndex(
                        name="test_document_embedding_idx_3072",
                        fields=["embedding"],
                        m=16,
                        ef_construction=64,
                        opclasses=["halfvec_cosine_ops"],
                    ),
                ],
            },
        ),
        CreateModelOnlySqlite(
            name="TestSQLiteDocument1536",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("page_content", models.TextField()),
                ("metadata", models.JSONField()),
                ("embedding", SQLiteVectorField(dimensions=1536)),
            ],
        ),
        CreateModelOnlySqlite(
            name="TestSQLiteDocument3072",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("page_content", models.TextField()),
                ("metadata", models.JSONField()),
                ("embedding", SQLiteVectorField(dimensions=1536 * 2)),
            ],
        ),
    ]
