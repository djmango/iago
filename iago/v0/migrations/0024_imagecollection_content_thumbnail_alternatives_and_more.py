# Generated by Django 4.0.4 on 2022-05-29 16:29

import django.contrib.postgres.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('v0', '0023_alter_content_updated_on'),
    ]

    operations = [
        migrations.CreateModel(
            name='ImageCollection',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('embedding_all_mpnet_base_v2', django.contrib.postgres.fields.ArrayField(base_field=models.FloatField(), size=768)),
                ('name', models.CharField(editable=False, max_length=50)),
                ('url', models.URLField(max_length=800, unique=True)),
                ('collection_id', models.CharField(editable=False, max_length=50)),
                ('provider', models.CharField(choices=[('unsplash', 'Unsplash'), ('pexels', 'Pexels'), ('shutterstock', 'Shutterstock')], max_length=30)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.AddField(
            model_name='content',
            name='thumbnail_alternatives',
            field=models.JSONField(default=dict),
        ),
        migrations.AlterField(
            model_name='topic',
            name='name',
            field=models.CharField(editable=False, max_length=255, primary_key=True, serialize=False),
        ),
    ]
