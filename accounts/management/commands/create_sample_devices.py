from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from accounts.models import Device
from django.utils import timezone
import random
import socket

User = get_user_model()

class Command(BaseCommand):
    help = 'Tạo dữ liệu thiết bị mẫu cho tài khoản người dùng'

    def add_arguments(self, parser):
        parser.add_argument('--username', type=str, help='Tên người dùng cụ thể')
        parser.add_argument('--count', type=int, default=3, help='Số lượng thiết bị mẫu')

    def handle(self, *args, **kwargs):
        username = kwargs.get('username')
        count = kwargs.get('count')

        # Danh sách các loại thiết bị
        device_types = ['mobile', 'tablet', 'desktop']
        
        # Danh sách tên thiết bị
        device_names = {
            'mobile': ['iPhone 12', 'iPhone 13', 'iPhone 14', 'Samsung Galaxy S22', 'Samsung Galaxy S23', 'Xiaomi 12', 'Xiaomi 13', 'Google Pixel 6', 'Google Pixel 7'],
            'tablet': ['iPad Pro', 'iPad Air', 'Samsung Galaxy Tab S8', 'Samsung Galaxy Tab S9', 'Xiaomi Pad 6', 'Lenovo Tab P12 Pro'],
            'desktop': ['Windows PC', 'MacBook Pro', 'MacBook Air', 'iMac', 'Lenovo ThinkPad', 'Dell XPS', 'HP Spectre', 'Asus ZenBook']
        }
        
        # Danh sách trình duyệt
        browsers = ['Chrome', 'Firefox', 'Safari', 'Edge', 'Opera']
        
        # Danh sách hệ điều hành
        operating_systems = {
            'mobile': ['iOS 16', 'iOS 17', 'Android 13', 'Android 14'],
            'tablet': ['iPadOS 16', 'iPadOS 17', 'Android 13', 'Android 14'],
            'desktop': ['Windows 11', 'Windows 10', 'macOS Ventura', 'macOS Sonoma', 'Ubuntu 22.04']
        }
        
        # Danh sách địa chỉ IP mẫu
        sample_ips = ['192.168.1.1', '10.0.0.1', '172.16.0.1', '127.0.0.1', '192.168.0.1']
        
        try:
            # Nếu có username cụ thể, chỉ tạo thiết bị cho người dùng đó
            if username:
                users = User.objects.filter(username=username)
                if not users.exists():
                    self.stdout.write(self.style.ERROR(f'Không tìm thấy người dùng: {username}'))
                    return
            else:
                # Lấy tất cả người dùng
                users = User.objects.all()
                
            if not users:
                self.stdout.write(self.style.ERROR('Không tìm thấy người dùng nào.'))
                return
                
            # Đếm tổng số thiết bị đã tạo
            total_devices = 0
                
            # Tạo thiết bị cho mỗi người dùng
            for user in users:
                # Xóa tất cả thiết bị hiện tại của người dùng (tuỳ chọn)
                # Device.objects.filter(user=user).delete()
                
                # Lấy địa chỉ IP hiện tại
                try:
                    # Tạo socket để lấy IP thực tế (nếu có thể)
                    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    s.connect(('8.8.8.8', 80))
                    current_ip = s.getsockname()[0]
                    s.close()
                except:
                    current_ip = '127.0.0.1'
                
                # Tạo thiết bị hiện tại (luôn là desktop)
                current_device = Device.objects.create(
                    user=user,
                    device_id=f'current_{user.username}_{timezone.now().timestamp()}',
                    device_type='desktop',
                    device_name=random.choice(device_names['desktop']),
                    browser='Chrome',
                    os='Windows 10',
                    ip_address=current_ip,
                    is_current=True,
                    last_active=timezone.now()
                )
                total_devices += 1
                
                # Tạo các thiết bị khác
                for i in range(count):
                    # Chọn ngẫu nhiên loại thiết bị
                    device_type = random.choice(device_types)
                    
                    # Tạo thiết bị
                    device = Device.objects.create(
                        user=user,
                        device_id=f'{user.username}_{device_type}_{i}_{timezone.now().timestamp()}',
                        device_type=device_type,
                        device_name=random.choice(device_names[device_type]),
                        browser=random.choice(browsers),
                        os=random.choice(operating_systems[device_type]),
                        ip_address=random.choice(sample_ips),
                        is_current=False,
                        # Thời gian hoạt động gần đây (1-7 ngày trước)
                        last_active=timezone.now() - timezone.timedelta(days=random.randint(1, 7), 
                                                              hours=random.randint(0, 23),
                                                              minutes=random.randint(0, 59))
                    )
                    total_devices += 1
                
                self.stdout.write(self.style.SUCCESS(f'Đã tạo {count+1} thiết bị cho {user.username}'))
            
            self.stdout.write(self.style.SUCCESS(f'Đã tạo tổng cộng {total_devices} thiết bị mẫu thành công!'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Lỗi: {str(e)}')) 