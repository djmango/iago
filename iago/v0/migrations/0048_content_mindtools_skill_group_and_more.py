# Generated by Django 4.0.6 on 2022-08-18 11:51

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('v0', '0047_alter_content_thumbnail'),
    ]

    operations = [
        migrations.AddField(
            model_name='content',
            name='mindtools_skill_group',
            field=models.ManyToManyField(to='v0.mindtoolsskillgroup'),
        ),
        migrations.AddField(
            model_name='content',
            name='mindtools_skill_subgroup',
            field=models.ManyToManyField(to='v0.mindtoolsskillsubgroup'),
        ),
    ]
