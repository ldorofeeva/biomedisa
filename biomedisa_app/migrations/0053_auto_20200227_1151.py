# Generated by Django 3.0.3 on 2020-02-27 10:51

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('biomedisa_app', '0052_auto_20200227_1147'),
    ]

    operations = [
        migrations.AlterField(
            model_name='upload',
            name='epochs',
            field=models.IntegerField(default=200, verbose_name='Number of epochs trained (AI)'),
        ),
        migrations.AlterField(
            model_name='upload',
            name='normalize',
            field=models.BooleanField(default=True, verbose_name='Normalize training data (AI)'),
        ),
        migrations.AlterField(
            model_name='upload',
            name='position',
            field=models.BooleanField(default=False, verbose_name='Consider voxel location (AI)'),
        ),
    ]
