from allauth.account.adapter import DefaultAccountAdapter
from django.shortcuts import redirect
from django.urls import reverse
import logging

logger = logging.getLogger(__name__)


# Không hiện banner xanh “Successfully signed in/out…” trên feed
_SILENT_ACCOUNT_MESSAGES = {
    'account/messages/logged_in.txt',
    'account/messages/logged_out.txt',
}


class AccountAdapter(DefaultAccountAdapter):
    """Gate login behind TOTP when the user has two-factor authentication enabled."""

    def add_message(
        self,
        request,
        level,
        message_template,
        message_context=None,
        extra_tags='',
    ):
        if message_template in _SILENT_ACCOUNT_MESSAGES:
            return
        return super().add_message(
            request,
            level,
            message_template,
            message_context=message_context,
            extra_tags=extra_tags,
        )

    def send_mail(self, template_prefix, email, context):
        """Không làm fail đăng ký/đăng nhập khi SMTP lỗi (quota Gmail, mạng…)."""
        try:
            return super().send_mail(template_prefix, email, context)
        except Exception as exc:
            logger.warning(
                'Không gửi được email (%s → %s): %s',
                template_prefix,
                email,
                exc,
            )
            return None

    def send_confirmation_mail(self, request, emailconfirmation, signup):
        try:
            return super().send_confirmation_mail(request, emailconfirmation, signup)
        except Exception as exc:
            logger.warning(
                'Không gửi được email xác nhận (%s): %s',
                getattr(getattr(emailconfirmation, 'email_address', None), 'email', '?'),
                exc,
            )
            return None

    def pre_login(self, request, user, **kwargs):
        try:
            response = super().pre_login(request, user, **kwargs)
        except Exception as exc:
            # SMTP / email confirmation lỗi không được chặn đăng nhập sau signup
            logger.warning('pre_login email step failed for user=%s: %s', getattr(user, 'pk', None), exc)
            response = None

        if response:
            return response

        if getattr(user, 'two_factor_auth', False) and getattr(user, 'two_factor_secret', None):
            if request.session.pop('two_factor_verified', None):
                return None
            request.session['pending_2fa_user_id'] = user.pk
            request.session['pending_2fa_backend'] = getattr(user, 'backend', None)
            return redirect(reverse('accounts:verify_two_factor_login'))

        return None

    def get_login_redirect_url(self, request):
        if request.session.get('pending_2fa_user_id'):
            return reverse('accounts:verify_two_factor_login')
        return super().get_login_redirect_url(request)

    def is_open_for_signup(self, request):
        """Closed beta: vẫn mở form, nhưng bắt buộc mã mời (INVITE_ONLY)."""
        return True
