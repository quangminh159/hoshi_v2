import os
import django

# Thiết lập Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from allauth.socialaccount.models import SocialApp
from django.contrib.sites.models import Site

def update_google_client():
    """Cập nhật thông tin client Google đồng nhất"""
    
    # Đọc thông tin từ file .env
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
    google_client_id = None
    google_client_secret = None
    
    with open(env_path, 'r') as f:
        for line in f:
            if line.startswith('GOOGLE_CLIENT_ID='):
                google_client_id = line.strip().split('=', 1)[1]
            elif line.startswith('GOOGLE_CLIENT_SECRET='):
                google_client_secret = line.strip().split('=', 1)[1]
    
    if not google_client_id or not google_client_secret:
        print("❌ Không tìm thấy thông tin GOOGLE_CLIENT_ID hoặc GOOGLE_CLIENT_SECRET trong file .env")
        return False
    
    print(f"Thông tin trong file .env:")
    print(f"GOOGLE_CLIENT_ID: {google_client_id}")
    print(f"GOOGLE_CLIENT_SECRET: {google_client_secret}")
    
    # Cập nhật hoặc tạo SocialApp cho Google
    site = Site.objects.get(id=1)
    
    try:
        # Kiểm tra xem đã có SocialApp cho Google chưa
        google_app = SocialApp.objects.filter(provider='google').first()
        
        if google_app:
            # Nếu đã có, cập nhật thông tin
            google_app.client_id = google_client_id
            google_app.secret = google_client_secret
            google_app.save()
            print(f"✅ Đã cập nhật SocialApp cho Google với ID: {google_app.id}")
        else:
            # Nếu chưa có, tạo mới
            google_app = SocialApp.objects.create(
                provider='google',
                name='Google',
                client_id=google_client_id,
                secret=google_client_secret
            )
            google_app.sites.add(site)
            print(f"✅ Đã tạo mới SocialApp cho Google với ID: {google_app.id}")
        
        # Kiểm tra liên kết với site
        if site not in google_app.sites.all():
            google_app.sites.add(site)
            print(f"✅ Đã thêm site {site.domain} cho SocialApp")
        
        return True
    
    except Exception as e:
        print(f"❌ Lỗi khi cập nhật SocialApp: {e}")
        return False

if __name__ == "__main__":
    print("=== CẬP NHẬT THÔNG TIN GOOGLE CLIENT ===")
    if update_google_client():
        print("\n=== HOÀN TẤT THÀNH CÔNG ===")
        print("Đã cập nhật thông tin Google client. Khởi động lại server để áp dụng thay đổi.")
    else:
        print("\n=== HOÀN TẤT KHÔNG THÀNH CÔNG ===")
        print("Không thể cập nhật thông tin Google client. Vui lòng kiểm tra lại.") 