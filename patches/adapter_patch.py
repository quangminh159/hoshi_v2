"""
Patched version of the SocialAccountAdapter to avoid MultipleObjectsReturned error.
This should be imported in your views.py file.
"""

from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.socialaccount.models import SocialApp

class FixedSocialAccountAdapter(DefaultSocialAccountAdapter):
    """
    A version of SocialAccountAdapter that avoids MultipleObjectsReturned error
    by getting the first app when multiple apps exist for the same provider.
    """
    
    def get_app(self, request, provider):
        """
        Get the first matching SocialApp for the given provider.
        This avoids the MultipleObjectsReturned error.
        """
        try:
            app = SocialApp.objects.filter(provider=provider.id).order_by('-id').first()
            if app is None:
                if request is None:
                    raise RuntimeError("Make sure you've configured a SocialApp in the database for provider %s" % provider.id)
                raise SocialApp.DoesNotExist()
            return app
        except SocialApp.DoesNotExist:
            if request is None:
                raise RuntimeError("Make sure you've configured a SocialApp in the database for provider %s" % provider.id)
            return None
