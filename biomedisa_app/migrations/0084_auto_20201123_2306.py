# Generated by Django 3.1.2 on 2020-11-23 22:06

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('biomedisa_app', '0083_upload_automatic_cropping'),
    ]

    operations = [
        migrations.AddField(
            model_name='upload',
            name='path_to_model',
            field=models.TextField(null=True),
        ),
        migrations.AddField(
            model_name='upload',
            name='validation_split',
            field=models.FloatField(default=0.0),
        ),
    ]
