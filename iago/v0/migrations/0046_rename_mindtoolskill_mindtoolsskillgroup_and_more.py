# Generated by Django 4.0.5 on 2022-07-20 08:09

import django.contrib.postgres.fields
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('v0', '0045_mindtoolskill'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='MindtoolSkill',
            new_name='MindtoolsSkillGroup',
        ),
        migrations.CreateModel(
            name='MindtoolsSkillSubgroup',
            fields=[
                ('name', models.CharField(editable=False, max_length=255, primary_key=True, serialize=False)),
                ('embedding_all_mpnet_base_v2', django.contrib.postgres.fields.ArrayField(base_field=models.FloatField(), size=768)),
                ('group', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='v0.mindtoolsskillgroup')),
            ],
            options={
                'abstract': False,
            },
        ),
    ]
