from django.db import migrations
from pgvector.django import VectorExtension


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        VectorExtension(),
    ]
