import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("doku", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="ExtractedInformation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("schema_name", models.CharField(blank=True, help_text="사용된 추출 스키마 이름", max_length=100)),
                (
                    "extraction_type",
                    models.CharField(
                        choices=[("universal", "Universal"), ("prebuilt", "Prebuilt")],
                        default="universal",
                        max_length=20,
                    ),
                ),
                (
                    "document_type",
                    models.CharField(blank=True, help_text="문서 타입 (prebuilt 추출 시)", max_length=50, null=True),
                ),
                ("extracted_data", models.JSONField(help_text="추출된 정보")),
                ("extraction_model", models.CharField(blank=True, max_length=100, null=True)),
                (
                    "extraction_cost",
                    models.DecimalField(
                        blank=True, decimal_places=4, help_text="추출 비용 (USD)", max_digits=10, null=True
                    ),
                ),
                ("error_message", models.TextField(blank=True, help_text="추출 실패 시 에러 메시지", null=True)),
                (
                    "document",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="extracted_information",
                        to="doku.document",
                    ),
                ),
            ],
            options={
                "verbose_name": "추출된 정보",
                "verbose_name_plural": "추출된 정보",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="extractedinformation",
            index=models.Index(fields=["document", "schema_name"], name="doku_extrac_documen_0a5d8a_idx"),
        ),
        migrations.AddIndex(
            model_name="extractedinformation",
            index=models.Index(fields=["extraction_type", "document_type"], name="doku_extrac_extract_6e4b3c_idx"),
        ),
    ]
