from django import forms
from .models import Post, Comment

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