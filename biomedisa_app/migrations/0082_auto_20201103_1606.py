# Generated by Django 3.1.2 on 2020-11-03 15:06

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('biomedisa_app', '0081_auto_20201030_1809'),
    ]

    operations = [
        migrations.AlterField(
            model_name='profile',
            name='storage_size',
            field=models.IntegerField(default=50),
        ),
    ]
