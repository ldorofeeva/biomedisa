# Generated by Django 3.0.4 on 2020-03-24 13:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('biomedisa_app', '0061_auto_20200322_1704'),
    ]

    operations = [
        migrations.AlterField(
            model_name='mushroomspot',
            name='status_klopapier',
            field=models.IntegerField(null=True),
        ),
        migrations.AlterField(
            model_name='mushroomspot',
            name='status_mehl',
            field=models.IntegerField(null=True),
        ),
        migrations.AlterField(
            model_name='mushroomspot',
            name='status_nudeln',
            field=models.IntegerField(null=True),
        ),
    ]
