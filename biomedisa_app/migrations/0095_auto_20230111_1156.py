# Generated by Django 3.2.6 on 2023-01-11 10:56

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('biomedisa_app', '0094_auto_20221004_1509'),
    ]

    operations = [
        migrations.AddField(
            model_name='upload',
            name='filters',
            field=models.CharField(default='32-64-128-256-512-1024', max_length=30, verbose_name='Network architecture (AI)'),
        ),
        migrations.AddField(
            model_name='upload',
            name='resnet',
            field=models.BooleanField(default=False, verbose_name='Use ResNet convolution blocks (AI)'),
        ),
    ]
