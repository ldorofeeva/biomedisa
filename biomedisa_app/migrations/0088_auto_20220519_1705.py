# Generated by Django 3.2.6 on 2022-05-19 15:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('biomedisa_app', '0087_processeddata_repository_specimen_tomographicdata'),
    ]

    operations = [
        migrations.AddField(
            model_name='repository',
            name='featured_img',
            field=models.TextField(null=True),
        ),
        migrations.AddField(
            model_name='repository',
            name='featured_img_height',
            field=models.TextField(null=True),
        ),
        migrations.AddField(
            model_name='repository',
            name='featured_img_width',
            field=models.TextField(null=True),
        ),
    ]