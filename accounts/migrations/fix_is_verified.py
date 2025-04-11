from django.db import migrations

def fix_is_verified(apps, schema_editor):
    User = apps.get_model('accounts', 'User')
    for user in User.objects.all():
        if not isinstance(user.is_verified, bool):
            user.is_verified = False  # Đặt giá trị mặc định là False
            user.save()

class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0001_initial'),  # Thay đổi tùy thuộc vào migration hiện tại của bạn
    ]

    operations = [
        migrations.RunPython(fix_is_verified),
    ] 