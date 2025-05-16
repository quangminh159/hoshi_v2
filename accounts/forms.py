from django import forms
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from allauth.account.forms import SignupForm as AllAuthSignupForm
from allauth.account.forms import ResetPasswordForm as AllAuthResetPasswordForm
from allauth.account.forms import ResetPasswordKeyForm as AllAuthResetPasswordKeyForm
from .models import User
from phonenumber_field.formfields import PhoneNumberField

User = get_user_model()

class CustomSignupForm(AllAuthSignupForm):
    username = forms.CharField(
        max_length=30, 
        label='Tên người dùng',
        widget=forms.TextInput(attrs={
            'placeholder': 'Tên người dùng',
            'class': 'form-control'
        })
    )
    email = forms.EmailField(
        label='Email',
        widget=forms.EmailInput(attrs={
            'placeholder': 'Email',
            'class': 'form-control'
        })
    )
    phone_number = PhoneNumberField(
        label='Số điện thoại',
        required=True,
        widget=forms.TextInput(attrs={
            'placeholder': 'Số điện thoại',
            'class': 'form-control',
            'type': 'tel'
        })
    )
    password1 = forms.CharField(
        label='Mật khẩu',
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Mật khẩu',
            'class': 'form-control'
        })
    )
    password2 = forms.CharField(
        label='Xác nhận mật khẩu',
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Xác nhận mật khẩu',
            'class': 'form-control'
        })
    )
    avatar = forms.ImageField(
        required=False,
        label='Ảnh đại diện',
        widget=forms.FileInput(attrs={
            'class': 'd-none',
            'accept': 'image/*'
        })
    )
    gender = forms.ChoiceField(
        label='Giới tính',
        choices=[
            ('M', 'Nam'),
            ('F', 'Nữ'),
            ('O', 'Khác')
        ],
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )

    def clean_username(self):
        username = self.cleaned_data['username']
        if User.objects.filter(username=username).exists():
            raise ValidationError('Tên người dùng này đã được sử dụng.')
        return username

    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email=email).exists():
            raise ValidationError('Email này đã được sử dụng.')
        return email

    def clean_phone_number(self):
        phone_number = self.cleaned_data['phone_number']
        if User.objects.filter(phone_number=phone_number).exists():
            raise ValidationError('Số điện thoại này đã được sử dụng.')
        return phone_number

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')
        
        if password1 and password2 and password1 != password2:
            raise ValidationError('Mật khẩu không khớp.')
        
        return cleaned_data

    def clean_gender(self):
        gender = self.cleaned_data.get('gender')
        if not gender:
            raise forms.ValidationError('Vui lòng chọn giới tính')
        return gender

    def save(self, request):
        # Lưu user từ form cha
        user = super().save(request)
        
        # Xử lý avatar
        avatar = self.cleaned_data.get('avatar')
        if avatar:
            user.avatar = avatar
        
        # Lưu giới tính
        user.gender = self.cleaned_data.get('gender')
        
        # Lưu số điện thoại
        user.phone_number = self.cleaned_data.get('phone_number')
        
        user.save()
        
        return user

class ProfileForm(forms.ModelForm):
    remove_avatar = forms.BooleanField(
        label='Xóa ảnh đại diện',
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )

    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'username', 'email', 
            'bio', 'website', 'facebook', 'twitter', 'instagram', 'linkedin',
            'avatar'
        ]
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['first_name'].widget.attrs.update({
            'placeholder': 'Tên',
            'class': 'form-control'
        })
        self.fields['last_name'].widget.attrs.update({
            'placeholder': 'Họ',
            'class': 'form-control'
        })
        self.fields['username'].widget.attrs.update({
            'placeholder': 'Tên người dùng',
            'class': 'form-control'
        })
        self.fields['email'].widget.attrs.update({
            'placeholder': 'Email',
            'class': 'form-control'
        })
        self.fields['bio'].widget.attrs.update({
            'placeholder': 'Giới thiệu về bạn',
            'rows': 3,
            'class': 'form-control'
        })
        self.fields['website'].widget.attrs.update({
            'placeholder': 'Website của bạn',
            'class': 'form-control'
        })
        self.fields['facebook'].widget.attrs.update({
            'placeholder': 'Link Facebook của bạn',
            'class': 'form-control'
        })
        self.fields['twitter'].widget.attrs.update({
            'placeholder': 'Link Twitter của bạn',
            'class': 'form-control'
        })
        self.fields['instagram'].widget.attrs.update({
            'placeholder': 'Link Instagram của bạn',
            'class': 'form-control'
        })
        self.fields['linkedin'].widget.attrs.update({
            'placeholder': 'Link LinkedIn của bạn',
            'class': 'form-control'
        })
        self.fields['avatar'].widget.attrs.update({
            'class': 'd-none',
            'accept': 'image/*'
        })
        
    def clean_username(self):
        username = self.cleaned_data['username']
        if User.objects.exclude(pk=self.instance.pk).filter(username=username).exists():
            raise forms.ValidationError('Tên người dùng này đã được sử dụng.')
        return username
        
    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.exclude(pk=self.instance.pk).filter(email=email).exists():
            raise forms.ValidationError('Email này đã được sử dụng.')
        return email

    def save(self, commit=True):
        # Kiểm tra xem có yêu cầu xóa avatar không
        if self.cleaned_data.get('remove_avatar'):
            # Nếu có avatar, xóa nó
            if self.instance.avatar:
                self.instance.avatar.delete()
                self.instance.avatar = None
        
        # Nếu có avatar mới được upload, sử dụng avatar mới
        if self.cleaned_data.get('avatar'):
            self.instance.avatar = self.cleaned_data['avatar']
        
        return super().save(commit)

class CustomPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['old_password'].widget.attrs.update({
            'placeholder': 'Mật khẩu hiện tại'
        })
        self.fields['new_password1'].widget.attrs.update({
            'placeholder': 'Mật khẩu mới'
        })
        self.fields['new_password2'].widget.attrs.update({
            'placeholder': 'Xác nhận mật khẩu mới'
        })

class NotificationSettingsForm(forms.ModelForm):
    class Meta:
        model = User
        fields = [
            'push_notifications', 
            'email_notifications',
            'like_notifications',
            'comment_notifications',
            'follow_notifications',
            'mention_notifications'
        ]

class PrivacySettingsForm(forms.ModelForm):
    class Meta:
        model = User
        fields = [
            'private_account',
            'hide_activity',
            'block_messages'
        ]

class SecuritySettingsForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['two_factor_auth']

class DeleteAccountForm(forms.Form):
    DELETE_REASONS = (
        ('privacy', 'Lo ngại về quyền riêng tư'),
        ('another_account', 'Có tài khoản khác'),
        ('not_useful', 'Không thấy hữu ích'),
        ('other', 'Lý do khác')
    )
    
    reason = forms.ChoiceField(
        choices=DELETE_REASONS,
        required=True,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        required=True
    )
    confirm = forms.BooleanField(required=True)
    
    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        
    def clean_password(self):
        password = self.cleaned_data['password']
        if not self.user.check_password(password):
            raise forms.ValidationError('Mật khẩu không chính xác.')
        return password 

class CustomResetPasswordForm(AllAuthResetPasswordForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].widget.attrs.update({
            'placeholder': 'Địa chỉ email của bạn',
            'class': 'form-control'
        })
        self.fields['email'].label = 'Email'

class CustomResetPasswordKeyForm(AllAuthResetPasswordKeyForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].widget.attrs.update({
            'placeholder': 'Mật khẩu mới',
            'class': 'form-control'
        })
        self.fields['password1'].label = 'Mật khẩu mới'
        
        self.fields['password2'].widget.attrs.update({
            'placeholder': 'Xác nhận mật khẩu mới',
            'class': 'form-control'
        })
        self.fields['password2'].label = 'Xác nhận mật khẩu mới' 