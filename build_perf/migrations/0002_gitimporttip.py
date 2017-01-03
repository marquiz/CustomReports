# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('build_perf', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='GitImportTip',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('branch', models.CharField(unique=True, max_length=80)),
                ('commit', models.CharField(max_length=40)),
            ],
        ),
    ]
