# Generated by Django 3.2.16 on 2023-04-03 14:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('user_profile', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='usersession',
            name='ip',
            field=models.CharField(max_length=32, null=True),
        ),
    ]