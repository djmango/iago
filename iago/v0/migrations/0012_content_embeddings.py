# Generated by Django 3.2.8 on 2021-11-24 20:25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('v0', '0011_auto_20211117_1622'),
    ]

    operations = [
        migrations.AddField(
            model_name='content',
            name='embeddings',
            field=models.JSONField(default=dict),
        ),
    ]
