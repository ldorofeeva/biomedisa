# Generated by Django 3.2.6 on 2023-02-22 17:11

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('biomedisa_app', '0099_auto_20230222_1804'),
    ]

    operations = [
        migrations.RenameField(
            model_name='tomographicdata',
            old_name='scintillator',
            new_name='filter',
        ),
        migrations.RenameField(
            model_name='tomographicdata',
            old_name='frames_s',
            new_name='frames_per_s',
        ),
    ]