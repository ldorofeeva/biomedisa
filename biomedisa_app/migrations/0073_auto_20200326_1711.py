# Generated by Django 3.0.4 on 2020-03-26 16:11

import biomedisa_app.models
import django.core.files.storage
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('biomedisa_app', '0072_auto_20200326_1658'),
    ]

    operations = [
        migrations.AlterField(
            model_name='upload',
            name='pic',
            field=models.FileField(storage=django.core.files.storage.FileSystemStorage(location='/home/philipp/git/biomedisa/private_storage/'), upload_to=biomedisa_app.models.user_directory_path, verbose_name=''),
        ),
    ]
