# Generated by Django 4.0.4 on 2022-05-30 13:12

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('v0', '0025_image_delete_imagecollection_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='image',
            name='name',
        ),
    ]
