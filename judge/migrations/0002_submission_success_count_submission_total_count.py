# Generated by Django 4.2.20 on 2025-04-08 03:54

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("judge", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="submission",
            name="success_count",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="submission",
            name="total_count",
            field=models.PositiveIntegerField(default=0),
        ),
    ]
