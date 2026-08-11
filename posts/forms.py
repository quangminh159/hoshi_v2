from django import forms
from .models import Post, Comment, PostReport

class PostForm(forms.ModelForm):
    """Form cho việc tạo và chỉnh sửa bài đăng"""
    
    caption = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Bạn đang nghĩ gì?'
        }),
        required=False
    )
    
    location = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Thêm vị trí'
        }),
        required=False
    )
    
    # Lưu ý: chúng ta bỏ trường media ở đây và xử lý nó riêng trong view
    
    class Meta:
        model = Post
        fields = ['caption', 'location', 'visibility']
        widgets = {
            'visibility': forms.Select(attrs={
                'class': 'form-select form-select-sm post-visibility-select',
            }),
        }
        labels = {
            'visibility': 'Chế độ xem',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['visibility'].choices = [
            (Post.VISIBILITY_PUBLIC, 'Công khai'),
            (Post.VISIBILITY_ONLY_ME, 'Chỉ mình tôi'),
        ]
        self.fields['visibility'].initial = (
            getattr(self.instance, 'visibility', None) or Post.VISIBILITY_PUBLIC
        )

class CommentForm(forms.ModelForm):
    """Form cho việc thêm bình luận"""
    
    text = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Thêm bình luận...',
            'aria-label': 'Thêm bình luận',
            'aria-describedby': 'button-addon2'
        }),
        max_length=500,
        required=False,
    )
    image = forms.ImageField(required=False)
    video = forms.FileField(required=False)
    audio = forms.FileField(required=False)
    
    class Meta:
        model = Comment
        fields = ['text', 'image', 'video', 'audio']

    def clean(self):
        cleaned = super().clean()
        text = (cleaned.get('text') or '').strip()
        image = cleaned.get('image')
        video = cleaned.get('video')
        audio = cleaned.get('audio')
        if not text and not image and not video and not audio:
            raise forms.ValidationError('Vui lòng nhập nội dung, chọn ảnh/video hoặc ghi âm.')
        cleaned['text'] = text
        return cleaned

class PostReportForm(forms.ModelForm):
    """Form báo cáo bài viết vi phạm"""
    details = forms.CharField(
        label='Chi tiết báo cáo',
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Mô tả chi tiết về vấn đề mà bạn gặp phải với bài viết này'
        }),
        required=False
    )
    
    class Meta:
        model = PostReport
        fields = ['reason', 'details']
        widgets = {
            'reason': forms.Select(attrs={'class': 'form-select'})
        }
        labels = {
            'reason': 'Lý do báo cáo'
        }
        
    def clean(self):
        cleaned_data = super().clean()
        reason = cleaned_data.get('reason')
        details = cleaned_data.get('details')
        
        # Nếu lý do là 'other', bắt buộc phải có chi tiết
        if reason == 'other' and not details:
            self.add_error('details', 'Vui lòng cung cấp chi tiết khi chọn "Khác" làm lý do báo cáo.')
            
        return cleaned_data 