from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="email_notifications_enabled",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="webhook_notifications_enabled",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="webhook_url",
            field=models.URLField(blank=True, null=True),
        ),
    ]
