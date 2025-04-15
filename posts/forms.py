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
        fields = ['caption', 'location']

class CommentForm(forms.ModelForm):
    """Form cho việc thêm bình luận"""
    
    text = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Thêm bình luận...',
            'aria-label': 'Thêm bình luận',
            'aria-describedby': 'button-addon2'
        }),
        max_length=500
    )
    
    class Meta:
        model = Comment
        fields = ['text']

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