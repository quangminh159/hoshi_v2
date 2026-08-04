from django import forms
from django.contrib.auth.forms import PasswordChangeForm, AuthenticationForm
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from allauth.account.forms import SignupForm as AllAuthSignupForm
from allauth.account.forms import ResetPasswordForm as AllAuthResetPasswordForm
from allauth.account.forms import ResetPasswordKeyForm as AllAuthResetPasswordKeyForm
from .models import User
from phonenumber_field.formfields import PhoneNumberField
from phonenumber_field.widgets import PhoneNumberPrefixWidget

User = get_user_model()


def international_phone_widget(initial_region='VN'):
    """Country-code selector + national number — accepts any country."""
    return PhoneNumberPrefixWidget(
        initial=initial_region,
        country_attrs={
            'class': 'form-select phone-country-select',
            'aria-label': 'Mã quốc gia',
        },
        number_attrs={
            'class': 'form-control',
            'placeholder': 'Số điện thoại',
            'type': 'tel',
            'inputmode': 'tel',
            'autocomplete': 'tel-national',
        },
    )

class CustomLoginForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Tên người dùng hoặc email'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Mật khẩu'
        })
    )

    error_messages = {
        'invalid_login': 'Tên đăng nhập hoặc mật khẩu không chính xác. Vui lòng thử lại.',
        'inactive': 'Tài khoản này đã bị vô hiệu hóa.',
    }

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
        region=None,
        widget=international_phone_widget(),
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
    agree_terms = forms.BooleanField(
        label='Đồng ý điều khoản',
        required=True,
        error_messages={
            'required': 'Bạn cần đồng ý với Điều khoản sử dụng và Chính sách bảo mật để tiếp tục.'
        },
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
            'id': 'id_agree_terms'
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

    def clean_agree_terms(self):
        agreed = self.cleaned_data.get('agree_terms')
        if not agreed:
            raise ValidationError(
                'Bạn cần đồng ý với Điều khoản sử dụng và Chính sách bảo mật để tiếp tục.'
            )
        return agreed

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
        
        # Đảm bảo tất cả các thông báo được bật mặc định
        user.push_notifications = True
        user.email_notifications = True
        user.like_notifications = True
        user.comment_notifications = True
        user.follow_notifications = True
        user.mention_notifications = True
        user.message_notifications = True
        user.summary_notifications = True
        user.inactive_notifications = True
        
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
        # email / phone đổi qua luồng OTP riêng
        fields = [
            'first_name', 'last_name', 'username',
            'birth_date', 'gender',
            'bio', 'website', 'facebook', 'twitter', 'instagram', 'linkedin',
            'avatar'
        ]
        widgets = {
            'birth_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control'
            }),
            'gender': forms.Select(attrs={
                'class': 'form-select'
            }),
        }

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
        self.fields['gender'].required = False
        self.fields['gender'].label = 'Giới tính'
        self.fields['birth_date'].label = 'Ngày sinh'
        self.fields['birth_date'].required = False

    def clean_username(self):
        username = self.cleaned_data['username']
        if User.objects.exclude(pk=self.instance.pk).filter(username=username).exists():
            raise forms.ValidationError('Tên người dùng này đã được sử dụng.')
        return username

    def save(self, commit=True):
        if self.cleaned_data.get('remove_avatar'):
            if self.instance.avatar:
                self.instance.avatar.delete()
                self.instance.avatar = None

        if self.cleaned_data.get('avatar'):
            self.instance.avatar = self.cleaned_data['avatar']

        return super().save(commit)


class ChangeEmailRequestForm(forms.Form):
    new_email = forms.EmailField(
        label='Email mới',
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nhập email mới'
        })
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_new_email(self):
        email = self.cleaned_data['new_email'].strip().lower()
        if email == (self.user.email or '').lower():
            raise forms.ValidationError('Email mới phải khác email hiện tại.')
        if User.objects.exclude(pk=self.user.pk).filter(email__iexact=email).exists():
            raise forms.ValidationError('Email này đã được sử dụng.')
        return email


class ChangePhoneRequestForm(forms.Form):
    new_phone = PhoneNumberField(
        label='Số điện thoại mới',
        region=None,
        widget=international_phone_widget(),
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_new_phone(self):
        phone = self.cleaned_data['new_phone']
        if self.user.phone_number and str(phone) == str(self.user.phone_number):
            raise forms.ValidationError('Số điện thoại mới phải khác số hiện tại.')
        if User.objects.exclude(pk=self.user.pk).filter(phone_number=phone).exists():
            raise forms.ValidationError('Số điện thoại này đã được sử dụng.')
        return phone


class ContactOtpVerifyForm(forms.Form):
    code = forms.CharField(
        label='Mã xác thực',
        min_length=6,
        max_length=8,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg text-center',
            'placeholder': '000000',
            'pattern': '[0-9]{6,8}',
            'autocomplete': 'one-time-code',
            'autofocus': True,
        })
    )

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
            'mention_notifications',
            'message_notifications',
            'summary_notifications',
            'inactive_notifications',
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        field_labels = {
            'push_notifications': ('Thông báo đẩy', 'pushNotifications'),
            'email_notifications': ('Thông báo qua email', 'emailNotifications'),
            'like_notifications': ('Lượt thích', 'likeNotifications'),
            'comment_notifications': ('Bình luận', 'commentNotifications'),
            'follow_notifications': ('Theo dõi', 'followNotifications'),
            'mention_notifications': ('Nhắc đến', 'mentionNotifications'),
            'message_notifications': ('Tin nhắn', 'messageNotifications'),
            'summary_notifications': ('Tóm tắt hàng tuần', 'summaryNotifications'),
            'inactive_notifications': ('Nhắc nhở không hoạt động', 'inactiveNotifications'),
        }
        for name, (label, field_id) in field_labels.items():
            self.fields[name].widget = forms.CheckboxInput(
                attrs={'class': 'form-check-input', 'id': field_id}
            )
            self.fields[name].label = label

class PrivacySettingsForm(forms.ModelForm):
    class Meta:
        model = User
        fields = [
            'private_account',
            'hide_activity',
            'block_messages'
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['private_account'].widget = forms.CheckboxInput(attrs={'class': 'form-check-input', 'id': 'privateAccount'})
        self.fields['hide_activity'].widget = forms.CheckboxInput(attrs={'class': 'form-check-input', 'id': 'hideActivity'})
        self.fields['block_messages'].widget = forms.CheckboxInput(attrs={'class': 'form-check-input', 'id': 'blockMessages'})

        self.fields['private_account'].label = 'Tài khoản riêng tư'
        self.fields['hide_activity'].label = 'Ẩn trạng thái hoạt động'
        self.fields['block_messages'].label = 'Chặn tin nhắn'
        self.fields['private_account'].help_text = (
            'Người khác phải gửi yêu cầu và được bạn xác nhận mới theo dõi được.'
        )

    def save(self, commit=True):
        was_private = bool(self.instance.pk and self.instance.is_account_private())
        user = super().save(commit=False)
        user.is_private = user.private_account
        if commit:
            user.save()
            if was_private and not user.is_account_private():
                from .follow_requests import accept_all_pending_for
                accept_all_pending_for(user)
        return user

class LanguageSettingsForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['language']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['language'].widget = forms.RadioSelect(attrs={
            'class': 'form-check-input language-option'
        })
        self.fields['language'].label = 'Ngôn ngữ hiển thị'
        self.fields['language'].choices = User.LANGUAGE_CHOICES


class DisableTwoFactorForm(forms.Form):
    password = forms.CharField(
        label='Mật khẩu',
        required=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Mật khẩu hiện tại'
        })
    )
    code = forms.CharField(
        label='Mã xác thực',
        required=False,
        max_length=6,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '000000',
            'pattern': '[0-9]{6}',
            'autocomplete': 'one-time-code'
        })
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        code = cleaned_data.get('code')

        if password and self.user.check_password(password):
            return cleaned_data

        if code and self.user.two_factor_secret:
            import pyotp
            totp = pyotp.TOTP(self.user.two_factor_secret)
            if totp.verify(code, valid_window=1):
                return cleaned_data

        raise forms.ValidationError(
            'Vui lòng nhập đúng mật khẩu hoặc mã xác thực 6 số từ ứng dụng.'
        )

class VerifyTwoFactorLoginForm(forms.Form):
    code = forms.CharField(
        label='Mã xác thực',
        max_length=6,
        min_length=6,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg text-center',
            'placeholder': '000000',
            'pattern': '[0-9]{6}',
            'autocomplete': 'one-time-code',
            'autofocus': True,
        })
    )

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
    """Cho phép đặt lại mật khẩu bằng email hoặc SĐT quốc tế (mọi quốc gia)."""

    METHOD_EMAIL = 'email'
    METHOD_PHONE = 'phone'
    METHOD_CHOICES = (
        (METHOD_EMAIL, 'Email'),
        (METHOD_PHONE, 'Số điện thoại'),
    )

    email = forms.EmailField(
        label='Email',
        required=False,
        widget=forms.EmailInput(
            attrs={
                'placeholder': 'you@email.com',
                'autocomplete': 'email',
                'class': 'form-control',
            }
        ),
    )
    phone_number = PhoneNumberField(
        label='Số điện thoại',
        required=False,
        region=None,
        widget=international_phone_widget('VN'),
    )
    method = forms.ChoiceField(
        choices=METHOD_CHOICES,
        required=False,
        initial=METHOD_EMAIL,
        widget=forms.RadioSelect,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.reset_via_phone = False
        self.reset_channel = self.METHOD_EMAIL
        self.users = []
        self.fields['email'].required = False
        self.fields['email'].label = 'Email'
        self.fields['phone_number'].label = 'Số điện thoại'
        # Prefix widget classes for auth-flow styling
        phone_widget = self.fields['phone_number'].widget
        if hasattr(phone_widget, 'widgets') and len(phone_widget.widgets) >= 2:
            country_w, number_w = phone_widget.widgets[0], phone_widget.widgets[1]
            country_w.attrs.update({
                'class': 'form-select phone-country-select auth-flow__phone-country',
                'aria-label': 'Mã quốc gia',
            })
            number_w.attrs.update({
                'class': 'form-control auth-flow__phone-national',
                'placeholder': 'Số điện thoại',
                'type': 'tel',
                'inputmode': 'tel',
                'autocomplete': 'tel-national',
            })

    @staticmethod
    def mask_phone(e164):
        digits = ''.join(ch for ch in str(e164) if ch.isdigit())
        if len(digits) < 4:
            return '****'
        return f'****{digits[-4:]}'

    def clean(self):
        from allauth.account.adapter import get_adapter
        from allauth.account.utils import filter_users_by_email
        from allauth.account import app_settings as allauth_app_settings

        cleaned = super().clean()
        method = (cleaned.get('method') or self.METHOD_EMAIL).strip()
        if method not in (self.METHOD_EMAIL, self.METHOD_PHONE):
            method = self.METHOD_EMAIL

        email = (cleaned.get('email') or '').strip()
        phone = cleaned.get('phone_number')

        # Cho phép suy luận method nếu JS không gửi
        if method == self.METHOD_EMAIL and not email and phone:
            method = self.METHOD_PHONE
        if method == self.METHOD_PHONE and not phone and email:
            method = self.METHOD_EMAIL

        self.reset_channel = method
        cleaned['method'] = method

        if method == self.METHOD_PHONE:
            if not phone:
                self.add_error(
                    'phone_number',
                    'Vui lòng chọn mã quốc gia và nhập số điện thoại hợp lệ.',
                )
                return cleaned

            phone_e164 = str(phone)
            self.users = list(
                User.objects.filter(phone_number=phone, is_active=True)[:1]
            )
            # Giữ key email để allauth rate-limit / tương thích
            cleaned['email'] = phone_e164
            return cleaned

        if not email:
            self.add_error('email', 'Vui lòng nhập email của bạn.')
            return cleaned

        email = get_adapter().clean_email(email)
        cleaned['email'] = email
        self.users = filter_users_by_email(email, is_active=True, prefer_verified=True)
        if not self.users and not allauth_app_settings.PREVENT_ENUMERATION:
            self.add_error('email', get_adapter().error_messages['unknown_email'])
        return cleaned

    def clean_email(self):
        # Bỏ validation bắt buộc của allauth; xử lý trong clean()
        return (self.cleaned_data.get('email') or '').strip()

    def save(self, request, **kwargs):
        if self.reset_channel == self.METHOD_PHONE:
            return self._save_phone_reset(request)
        return super().save(request, **kwargs)

    def _save_phone_reset(self, request):
        from .otp_utils import (
            generate_otp,
            store_otp,
            is_in_cooldown,
            is_otp_locked,
            deliver_password_reset_otp,
            PASSWORD_RESET_NEUTRAL_MESSAGE,
        )

        self.reset_via_phone = True
        phone = str(self.cleaned_data.get('phone_number') or self.cleaned_data.get('email'))
        request.session['pwd_reset_hint'] = self.mask_phone(phone)
        request.session['pwd_reset_channel'] = 'phone'
        request.session.pop('pwd_reset_uid', None)
        request.session['pwd_reset_message'] = PASSWORD_RESET_NEUTRAL_MESSAGE

        if not self.users:
            return phone

        user = self.users[0]

        if is_otp_locked(user.id, 'password_reset'):
            # Không tiết lộ trạng thái khóa khác message trung tính
            return phone

        if is_in_cooldown(user.id, 'password_reset'):
            # Giữ uid để nhập mã đã gửi trước đó, message vẫn trung tính
            request.session['pwd_reset_uid'] = user.id
            return phone

        code = generate_otp(8)
        store_otp(user.id, 'password_reset', code, {})
        result = deliver_password_reset_otp(user, code)
        if result.get('ok'):
            request.session['pwd_reset_uid'] = user.id
        else:
            from .otp_utils import clear_otp
            clear_otp(user.id, 'password_reset')
        return phone


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