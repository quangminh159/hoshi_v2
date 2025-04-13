import os
import django
import sys
from decouple import config
from dotenv import load_dotenv
import traceback

# Thiết lập môi trường Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hoshi.settings')
django.setup()

# Import các model sau khi đã thiết lập Django
from django.contrib.sites.models import Site
from allauth.socialaccount.models import SocialApp

def main():
    try:
        # Tải biến môi trường từ file .env
        load_dotenv()
        
        # Lấy thông tin client từ biến môi trường
        facebook_client_id = config('FACEBOOK_CLIENT_ID', default=None)
        facebook_client_secret = config('FACEBOOK_CLIENT_SECRET', default=None)
        
        if not facebook_client_id or not facebook_client_secret:
            print("Lỗi: Không tìm thấy FACEBOOK_CLIENT_ID hoặc FACEBOOK_CLIENT_SECRET trong file .env")
            return
        
        print(f"FACEBOOK_CLIENT_ID: {facebook_client_id}")
        print(f"FACEBOOK_CLIENT_SECRET: {facebook_client_secret}")
        
        # Lấy hoặc tạo đối tượng Site
        site = Site.objects.get_current()
        print(f"Đang cập nhật thông tin Facebook client cho site: {site.domain}")
        
        # Tìm hoặc tạo SocialApp cho Facebook
        try:
            social_app = SocialApp.objects.get(provider='facebook')
            print(f"Đã tìm thấy ứng dụng Facebook hiện tại (ID: {social_app.id})")
        except SocialApp.DoesNotExist:
            social_app = SocialApp(provider='facebook')
            print("Đang tạo ứng dụng Facebook mới")
        except SocialApp.MultipleObjectsReturned:
            # Nếu có nhiều SocialApp, sử dụng cái đầu tiên
            social_app = SocialApp.objects.filter(provider='facebook').first()
            print(f"Cảnh báo: Có nhiều ứng dụng Facebook. Đang sử dụng ứng dụng có ID: {social_app.id}")
        
        # Cập nhật thông tin
        social_app.name = 'Facebook'
        social_app.client_id = facebook_client_id
        social_app.secret = facebook_client_secret
        social_app.save()
        
        # Đảm bảo SocialApp được liên kết với Site
        if site not in social_app.sites.all():
            social_app.sites.add(site)
        
        print(f"Đã cập nhật thành công thông tin Facebook client (ID: {social_app.id})")
        print("Hãy khởi động lại server để áp dụng thay đổi")
        
    except Exception as e:
        print(f"Lỗi khi cập nhật thông tin Facebook client: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    main() 