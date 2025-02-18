from django.db import migrations, models
from pgvector.django import HnswIndex, VectorField


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="TestDocument",
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
                # embedding 필드는 차원을 1536로 설정한 VectorField를 사용합니다.
                ("embedding", VectorField(dimensions=1536)),
            ],
            options={
                "indexes": [
                    HnswIndex(
                        name="test_document_embedding_idx",
                        fields=["embedding"],
                        m=16,
                        ef_construction=64,
                        opclasses=["vector_cosine_ops"],
                    ),
                ],
            },
        ),
    ]
