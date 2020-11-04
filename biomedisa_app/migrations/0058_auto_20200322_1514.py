# Generated by Django 3.0.4 on 2020-03-22 14:14

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('biomedisa_app', '0057_auto_20200322_1502'),
    ]

    operations = [
        migrations.RenameField(
            model_name='mushroomspot',
            old_name='status',
            new_name='status_klopapier',
        ),
        migrations.AddField(
            model_name='mushroomspot',
            name='status_mehl',
            field=models.ImageField(null=True, upload_to=''),
        ),
        migrations.AddField(
            model_name='mushroomspot',
            name='status_nudeln',
            field=models.ImageField(null=True, upload_to=''),
        ),
    ]
