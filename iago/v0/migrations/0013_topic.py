# Generated by Django 3.2.8 on 2021-11-28 04:41

import django.contrib.postgres.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('v0', '0012_content_embeddings'),
    ]

    operations = [
        migrations.CreateModel(
            name='Topic',
            fields=[
                ('name', models.CharField(editable=False, max_length=25, primary_key=True, serialize=False)),
                ('embedding_all_mpnet_base_v2', django.contrib.postgres.fields.ArrayField(base_field=models.FloatField(), size=768)),
            ],
        ),
    ]
