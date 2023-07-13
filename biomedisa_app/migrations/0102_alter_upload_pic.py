# Generated by Django 3.2.6 on 2023-07-12 04:34

import biomedisa_app.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('biomedisa_app', '0101_auto_20230704_0405'),
    ]

    operations = [
        migrations.AlterField(
            model_name='upload',
            name='pic',
            field=models.FileField(storage=biomedisa_app.models.MyFileSystemStorage(), upload_to=biomedisa_app.models.user_directory_path, validators=[biomedisa_app.models.validate_file_size], verbose_name=''),
        ),
    ]