from django.db import migrations

def ensure_boolean_values(apps, schema_editor):
    User = apps.get_model('accounts', 'User')
    for user in User.objects.all():
        # Đọc trực tiếp từ db_column
        user._is_verified = False
        user.save()

class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0004_alter_historicaluser_is_verified_and_more'),
    ]

    operations = [
        migrations.RunPython(ensure_boolean_values),
    ] 