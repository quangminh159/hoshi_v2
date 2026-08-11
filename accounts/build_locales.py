"""Generate django.po / django.mo locale catalogs for Moora UI strings."""
from pathlib import Path

import polib
from django.conf import settings

# msgid is Vietnamese (source language of the templates)
TRANSLATIONS = {
    'en': {
        'Moora - Mạng xã hội chia sẻ khoảnh khắc': 'Moora - Share your moments',
        'Trang chủ': 'Home',
        'Menu': 'Menu',
        'Tìm kiếm...': 'Search...',
        'Tìm kiếm': 'Search',
        'Tin nhắn': 'Messages',
        'Tạo bài viết': 'Create post',
        'Thông báo': 'Notifications',
        'thông báo chưa đọc': 'unread notifications',
        'Đánh dấu tất cả là đã đọc': 'Mark all as read',
        '%(time)s trước': '%(time)s ago',
        'Bạn không có thông báo nào': 'You have no notifications',
        'Xem tất cả thông báo': 'View all notifications',
        'Trang cá nhân': 'Profile',
        'Đã lưu': 'Saved',
        'Cài đặt': 'Settings',
        'Đăng xuất': 'Log out',
        'Đăng nhập': 'Log in',
        'Đăng ký': 'Sign up',
        'Đóng': 'Close',
        'Đã thích': 'Liked',
        'Điều hướng nhanh': 'Quick navigation',
        'Chỉnh sửa hồ sơ': 'Edit profile',
        'Đổi mật khẩu': 'Change password',
        'Quyền riêng tư': 'Privacy',
        'Ngôn ngữ': 'Language',
        'Bảo mật': 'Security',
        'Thiết bị đăng nhập': 'Login devices',
        'Tải xuống dữ liệu': 'Download data',
        'Xóa tài khoản': 'Delete account',
        'Cài đặt ngôn ngữ': 'Language settings',
        'Chọn ngôn ngữ hiển thị cho tài khoản của bạn. Tùy chọn này sẽ được lưu và áp dụng mỗi khi bạn đăng nhập.':
            'Choose the display language for your account. This preference is saved and applied every time you sign in.',
        'Ngôn ngữ hiển thị': 'Display language',
        'Lưu ngôn ngữ': 'Save language',
        'Đã cập nhật ngôn ngữ hiển thị.': 'Display language updated.',
    },
    'ja': {
        'Moora - Mạng xã hội chia sẻ khoảnh khắc': 'Moora - 瞬間をシェア',
        'Trang chủ': 'ホーム',
        'Menu': 'メニュー',
        'Tìm kiếm...': '検索...',
        'Tìm kiếm': '検索',
        'Tin nhắn': 'メッセージ',
        'Tạo bài viết': '投稿を作成',
        'Thông báo': '通知',
        'thông báo chưa đọc': '未読の通知',
        'Đánh dấu tất cả là đã đọc': 'すべて既読にする',
        '%(time)s trước': '%(time)s前',
        'Bạn không có thông báo nào': '通知はありません',
        'Xem tất cả thông báo': 'すべての通知を見る',
        'Trang cá nhân': 'プロフィール',
        'Đã lưu': '保存済み',
        'Cài đặt': '設定',
        'Đăng xuất': 'ログアウト',
        'Đăng nhập': 'ログイン',
        'Đăng ký': '新規登録',
        'Đóng': '閉じる',
        'Đã thích': 'いいね',
        'Điều hướng nhanh': 'クイックナビ',
        'Chỉnh sửa hồ sơ': 'プロフィール編集',
        'Đổi mật khẩu': 'パスワード変更',
        'Quyền riêng tư': 'プライバシー',
        'Ngôn ngữ': '言語',
        'Bảo mật': 'セキュリティ',
        'Thiết bị đăng nhập': 'ログイン端末',
        'Tải xuống dữ liệu': 'データダウンロード',
        'Xóa tài khoản': 'アカウント削除',
        'Cài đặt ngôn ngữ': '言語設定',
        'Chọn ngôn ngữ hiển thị cho tài khoản của bạn. Tùy chọn này sẽ được lưu và áp dụng mỗi khi bạn đăng nhập.':
            'アカウントの表示言語を選択してください。この設定は保存され、ログイン時に適用されます。',
        'Ngôn ngữ hiển thị': '表示言語',
        'Lưu ngôn ngữ': '言語を保存',
        'Đã cập nhật ngôn ngữ hiển thị.': '表示言語を更新しました。',
    },
    'ko': {
        'Moora - Mạng xã hội chia sẻ khoảnh khắc': 'Moora - 순간을 공유하세요',
        'Trang chủ': '홈',
        'Menu': '메뉴',
        'Tìm kiếm...': '검색...',
        'Tìm kiếm': '검색',
        'Tin nhắn': '메시지',
        'Tạo bài viết': '게시물 작성',
        'Thông báo': '알림',
        'thông báo chưa đọc': '읽지 않은 알림',
        'Đánh dấu tất cả là đã đọc': '모두 읽음으로 표시',
        '%(time)s trước': '%(time)s 전',
        'Bạn không có thông báo nào': '알림이 없습니다',
        'Xem tất cả thông báo': '모든 알림 보기',
        'Trang cá nhân': '프로필',
        'Đã lưu': '저장됨',
        'Cài đặt': '설정',
        'Đăng xuất': '로그아웃',
        'Đăng nhập': '로그인',
        'Đăng ký': '회원가입',
        'Đóng': '닫기',
        'Đã thích': '좋아요',
        'Điều hướng nhanh': '빠른 탐색',
        'Chỉnh sửa hồ sơ': '프로필 수정',
        'Đổi mật khẩu': '비밀번호 변경',
        'Quyền riêng tư': '개인정보',
        'Ngôn ngữ': '언어',
        'Bảo mật': '보안',
        'Thiết bị đăng nhập': '로그인 기기',
        'Tải xuống dữ liệu': '데이터 다운로드',
        'Xóa tài khoản': '계정 삭제',
        'Cài đặt ngôn ngữ': '언어 설정',
        'Chọn ngôn ngữ hiển thị cho tài khoản của bạn. Tùy chọn này sẽ được lưu và áp dụng mỗi khi bạn đăng nhập.':
            '계정의 표시 언어를 선택하세요. 이 설정은 저장되며 로그인할 때마다 적용됩니다.',
        'Ngôn ngữ hiển thị': '표시 언어',
        'Lưu ngôn ngữ': '언어 저장',
        'Đã cập nhật ngôn ngữ hiển thị.': '표시 언어가 업데이트되었습니다.',
    },
    'zh_Hans': {
        'Moora - Mạng xã hội chia sẻ khoảnh khắc': 'Moora - 分享你的瞬间',
        'Trang chủ': '首页',
        'Menu': '菜单',
        'Tìm kiếm...': '搜索...',
        'Tìm kiếm': '搜索',
        'Tin nhắn': '私信',
        'Tạo bài viết': '创建帖子',
        'Thông báo': '通知',
        'thông báo chưa đọc': '未读通知',
        'Đánh dấu tất cả là đã đọc': '全部标为已读',
        '%(time)s trước': '%(time)s前',
        'Bạn không có thông báo nào': '暂无通知',
        'Xem tất cả thông báo': '查看全部通知',
        'Trang cá nhân': '个人主页',
        'Đã lưu': '已收藏',
        'Cài đặt': '设置',
        'Đăng xuất': '退出登录',
        'Đăng nhập': '登录',
        'Đăng ký': '注册',
        'Đóng': '关闭',
        'Đã thích': '已点赞',
        'Điều hướng nhanh': '快捷导航',
        'Chỉnh sửa hồ sơ': '编辑资料',
        'Đổi mật khẩu': '修改密码',
        'Quyền riêng tư': '隐私',
        'Ngôn ngữ': '语言',
        'Bảo mật': '安全',
        'Thiết bị đăng nhập': '登录设备',
        'Tải xuống dữ liệu': '下载数据',
        'Xóa tài khoản': '删除账号',
        'Cài đặt ngôn ngữ': '语言设置',
        'Chọn ngôn ngữ hiển thị cho tài khoản của bạn. Tùy chọn này sẽ được lưu và áp dụng mỗi khi bạn đăng nhập.':
            '选择账户的显示语言。此偏好会保存，并在每次登录时应用。',
        'Ngôn ngữ hiển thị': '显示语言',
        'Lưu ngôn ngữ': '保存语言',
        'Đã cập nhật ngôn ngữ hiển thị.': '显示语言已更新。',
    },
}


def build_catalog(lang_code: str, mapping: dict) -> polib.POFile:
    po = polib.POFile()
    po.metadata = {
        'Project-Id-Version': 'hoshi',
        'Language': lang_code.replace('_', '-'),
        'MIME-Version': '1.0',
        'Content-Type': 'text/plain; charset=utf-8',
        'Content-Transfer-Encoding': '8bit',
    }
    for msgid, msgstr in mapping.items():
        entry = polib.POEntry(msgid=msgid, msgstr=msgstr)
        po.append(entry)
    return po


def main():
    base = Path(__file__).resolve().parent.parent / 'locale'
    for lang, mapping in TRANSLATIONS.items():
        dest = base / lang / 'LC_MESSAGES'
        dest.mkdir(parents=True, exist_ok=True)
        po = build_catalog(lang, mapping)
        po_path = dest / 'django.po'
        mo_path = dest / 'django.mo'
        po.save(po_path)
        po.save_as_mofile(mo_path)
        print(f'Wrote {po_path} ({len(mapping)} strings)')


if __name__ == '__main__':
    main()
