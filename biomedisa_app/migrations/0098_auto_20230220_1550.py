# Generated by Django 3.2.6 on 2023-02-20 14:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('biomedisa_app', '0097_alter_upload_resnet'),
    ]

    operations = [
        migrations.RenameField(
            model_name='specimen',
            old_name='collection_event_code',
            new_name='collection_code',
        ),
        migrations.RenameField(
            model_name='specimen',
            old_name='antwiki_source',
            new_name='source',
        ),
        migrations.AddField(
            model_name='specimen',
            name='for_more_specimen',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='specimen',
            name='lts_box',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name='LTS Box'),
        ),
        migrations.AddField(
            model_name='specimen',
            name='magnification',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='specimen',
            name='name_recommended',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='specimen',
            name='specimens_left',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]
