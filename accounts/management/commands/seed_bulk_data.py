"""
Tạo hàng loạt tài khoản + bài viết để test tải / concurrent.

Ví dụ:
  python manage.py seed_bulk_data --users 30 --posts-per-user 5
  python manage.py seed_bulk_data --users 20 --posts-per-user 3 --follow --likes
  python manage.py seed_bulk_data --clear
"""

from __future__ import annotations

import io
import random
from concurrent.futures import ThreadPoolExecutor, as_completed

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from accounts.models import UserFollowing
from posts.models import Comment, Like, Post, PostMedia

User = get_user_model()

CAPTIONS = [
    'Xin chào Moora! #{tag}',
    'Ngày mới năng lượng #{tag}',
    'Check-in nhanh #{tag}',
    'Chia sẻ khoảnh khắc #{tag}',
    'Test tải server #{tag}',
    'Bài viết mẫu #{tag} — concurrent test',
    'Feed đang chạy mượt không? #{tag}',
    'Hello world từ seed tool #{tag}',
]

TAGS = ['hoshi', 'test', 'load', 'feed', 'social', 'demo', 'vn', 'dev']


def _make_image_bytes(seed: int, size: int = 480) -> bytes:
    """Tạo ảnh JPEG đơn giản bằng Pillow (màu theo seed)."""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        # Minimal JPEG header fallback — không dùng nếu thiếu Pillow
        raise RuntimeError('Cần Pillow để tạo ảnh mẫu. pip install Pillow')

    random.seed(seed)
    color = (
        random.randint(40, 220),
        random.randint(40, 220),
        random.randint(40, 220),
    )
    img = Image.new('RGB', (size, size), color)
    draw = ImageDraw.Draw(img)
    text = f'#{seed}'
    draw.rectangle([20, 20, size - 20, size - 20], outline=(255, 255, 255), width=4)
    draw.text((size // 3, size // 2 - 10), text, fill=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format='JPEG', quality=75)
    return buf.getvalue()


class Command(BaseCommand):
    help = 'Tạo nhiều tài khoản và bài viết cùng lúc (load-test seed)'

    def add_arguments(self, parser):
        parser.add_argument('--users', type=int, default=20, help='Số tài khoản tạo mới (mặc định 20)')
        parser.add_argument(
            '--posts-per-user',
            type=int,
            default=3,
            help='Số bài viết mỗi tài khoản (mặc định 3)',
        )
        parser.add_argument(
            '--password',
            type=str,
            default='Test123456!',
            help='Mật khẩu chung cho tài khoản seed',
        )
        parser.add_argument(
            '--prefix',
            type=str,
            default='loaduser',
            help='Tiền tố username (mặc định loaduser)',
        )
        parser.add_argument(
            '--workers',
            type=int,
            default=4,
            help='Số thread tạo song song (mặc định 4)',
        )
        parser.add_argument(
            '--follow',
            action='store_true',
            help='Cho các user seed follow lẫn nhau ngẫu nhiên',
        )
        parser.add_argument(
            '--likes',
            action='store_true',
            help='Tạo like ngẫu nhiên giữa các user seed',
        )
        parser.add_argument(
            '--comments',
            action='store_true',
            help='Tạo vài bình luận ngẫu nhiên',
        )
        parser.add_argument(
            '--no-media',
            action='store_true',
            help='Chỉ tạo caption, không gắn ảnh',
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Xóa toàn bộ user (và bài viết) có prefix trước khi tạo',
        )
        parser.add_argument(
            '--start',
            type=int,
            default=1,
            help='Số bắt đầu cho username (loaduser1, loaduser2, ...)',
        )

    def handle(self, *args, **options):
        users_n = max(0, options['users'])
        posts_per_user = max(0, options['posts_per_user'])
        password = options['password']
        prefix = options['prefix'].strip() or 'loaduser'
        workers = max(1, options['workers'])
        start = max(1, options['start'])
        with_media = not options['no_media']

        if options['clear']:
            deleted = self._clear_prefix(prefix)
            self.stdout.write(self.style.WARNING(f'Deleted {deleted} users with prefix="{prefix}"'))
            if users_n == 0:
                return

        if users_n == 0:
            self.stdout.write(self.style.ERROR('Nothing to create. Use --users N'))
            return

        self.stdout.write(
            f'Creating {users_n} users (prefix={prefix}), '
            f'{posts_per_user} posts/user, workers={workers}...'
        )

        created_users = self._create_users(prefix, start, users_n, password, workers)
        self.stdout.write(self.style.SUCCESS(f'Users ready: {len(created_users)}'))

        posts = []
        if posts_per_user > 0 and created_users:
            posts = self._create_posts(created_users, posts_per_user, with_media, workers)
            self.stdout.write(self.style.SUCCESS(f'Posts created: {len(posts)}'))

        if options['follow'] and len(created_users) > 1:
            n = self._create_follows(created_users)
            self.stdout.write(self.style.SUCCESS(f'Follows: {n}'))

        if options['likes'] and posts and created_users:
            n = self._create_likes(created_users, posts)
            self.stdout.write(self.style.SUCCESS(f'Likes: {n}'))

        if options['comments'] and posts and created_users:
            n = self._create_comments(created_users, posts)
            self.stdout.write(self.style.SUCCESS(f'Comments: {n}'))

        sample = created_users[0]
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('Done.'))
        self.stdout.write(f'  Login: {sample.username} / {password}')
        self.stdout.write(f'  Usernames: {prefix}{start} ... {prefix}{start + users_n - 1}')

    def _clear_prefix(self, prefix: str) -> int:
        qs = User.objects.filter(username__startswith=prefix)
        count = qs.count()
        qs.delete()
        return count

    def _create_users(self, prefix, start, count, password, workers):
        specs = []
        for i in range(start, start + count):
            username = f'{prefix}{i}'
            email = f'{username}@example.com'
            specs.append((username, email, password, i))

        created = []
        existing = {
            u.username: u
            for u in User.objects.filter(username__startswith=prefix)
        }

        def create_one(spec):
            username, email, pwd, idx = spec
            if username in existing:
                return existing[username]
            user = User(
                username=username,
                email=email,
                bio=f'Tài khoản seed load-test #{idx}',
            )
            user.set_password(pwd)
            user.save()
            return user

        # User creation with set_password is CPU-bound; threads OK for SQLite with WAL
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = [pool.submit(create_one, s) for s in specs]
            for fut in as_completed(futures):
                created.append(fut.result())

        created.sort(key=lambda u: u.username)
        return created

    def _create_posts(self, users, posts_per_user, with_media, workers):
        jobs = []
        for user in users:
            for n in range(posts_per_user):
                jobs.append((user.id, user.username, n, with_media))

        posts = []

        def create_post(job):
            user_id, username, n, attach_media = job
            tag = random.choice(TAGS)
            caption = random.choice(CAPTIONS).format(tag=tag)
            with transaction.atomic():
                post = Post.objects.create(
                    author_id=user_id,
                    caption=caption,
                    location=random.choice(['Hà Nội', 'TP.HCM', 'Đà Nẵng', '', 'Online']),
                )
                if attach_media:
                    seed = user_id * 1000 + n
                    data = _make_image_bytes(seed)
                    media = PostMedia(post=post, media_type='image', order=0)
                    media.file.save(f'seed_{username}_{n}.jpg', ContentFile(data), save=True)
            return post

        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = [pool.submit(create_post, j) for j in jobs]
            for i, fut in enumerate(as_completed(futures), 1):
                posts.append(fut.result())
                if i % 20 == 0 or i == len(jobs):
                    self.stdout.write(f'  ... posts {i}/{len(jobs)}')

        return posts

    def _create_follows(self, users) -> int:
        created = 0
        for user in users:
            others = [u for u in users if u.id != user.id]
            targets = random.sample(others, k=min(len(others), random.randint(1, min(5, len(others)))))
            for target in targets:
                _, was_created = UserFollowing.objects.get_or_create(
                    user=user,
                    following_user=target,
                )
                if was_created:
                    created += 1
        return created

    def _create_likes(self, users, posts) -> int:
        created = 0
        for post in posts:
            likers = random.sample(users, k=min(len(users), random.randint(0, min(8, len(users)))))
            for user in likers:
                if user.id == post.author_id:
                    continue
                _, was_created = Like.objects.get_or_create(user=user, post=post)
                if was_created:
                    created += 1
            post.likes_count = post.post_likes.count()
            post.save(update_fields=['likes_count'])
        return created

    def _create_comments(self, users, posts) -> int:
        created = 0
        phrases = [
            'Hay quá!',
            'Nice shot',
            'Đỉnh!',
            'Seed comment test',
            'Like bài này',
            '🔥',
        ]
        for post in random.sample(posts, k=min(len(posts), max(1, len(posts) // 2))):
            if post.disable_comments:
                continue
            for _ in range(random.randint(1, 3)):
                author = random.choice(users)
                Comment.objects.create(
                    post=post,
                    author=author,
                    text=random.choice(phrases),
                )
                created += 1
            post.comments_count = post.comments.count()
            post.save(update_fields=['comments_count'])
        return created
