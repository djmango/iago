# Generated by Django 4.0.3 on 2022-03-23 15:26

from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('v0', '0015_job_skill'),
    ]

    operations = [
        migrations.CreateModel(
            name='ScrapedArticle',
            fields=[
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('url', models.URLField(max_length=800, unique=True)),
                ('author', models.TextField()),
                ('title', models.TextField()),
                ('thumbnail', models.URLField(null=True)),
                ('content', models.TextField()),
                ('content_read_seconds', models.IntegerField()),
                ('provider', models.CharField(max_length=100)),
                ('created_on', models.DateTimeField(auto_now_add=True)),
                ('updated_on', models.DateTimeField(auto_now_add=True)),
                ('tags', models.JSONField(default=list)),
            ],
        ),
    ]
