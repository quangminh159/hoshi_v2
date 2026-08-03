from allauth.account.adapter import DefaultAccountAdapter
from django.shortcuts import redirect
from django.urls import reverse


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

    def pre_login(self, request, user, **kwargs):
        response = super().pre_login(request, user, **kwargs)
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
