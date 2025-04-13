#!/usr/bin/env python
import os
import sys
import django
import time

# Thiết lập môi trường Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hoshi.settings_render')
django.setup()

try:
    from allauth.socialaccount.models import SocialApp
    from django.contrib.sites.models import Site
    from django.db import models
    from django.core.exceptions import MultipleObjectsReturned
    print("Đã import các module cần thiết thành công")
except ImportError as e:
    print(f"Lỗi import module: {e}")
    sys.exit(1)

def fix_signup_template():
    """Kiểm tra và sửa template đăng ký nếu cần"""
    try:
        from django.template.loader import get_template
        from django.template import TemplateDoesNotExist
        
        try:
            # Kiểm tra xem template đăng ký tồn tại không
            template = get_template('account/signup.html')
            print("Template đăng ký đã tồn tại")
        except TemplateDoesNotExist:
            # Nếu không tìm thấy template, tạo mới
            import os
            template_dir = os.path.join('templates', 'account')
            os.makedirs(template_dir, exist_ok=True)
            
            # Tạo template đăng ký cơ bản
            signup_template = """{% extends "base.html" %}

{% load i18n %}
{% load account socialaccount %}

{% block head_title %}{% trans "Signup" %}{% endblock %}

{% block content %}
<div class="container mt-5">
  <div class="row justify-content-center">
    <div class="col-md-6">
      <div class="card">
        <div class="card-header bg-primary text-white">
          <h1 class="h4 mb-0">{% trans "Sign Up" %}</h1>
        </div>
        <div class="card-body">
          <p>{% blocktrans %}Already have an account? Then please <a href="{{ login_url }}">sign in</a>.{% endblocktrans %}</p>

          <form class="signup" id="signup_form" method="post" action="{% url 'account_signup' %}">
            {% csrf_token %}
            {{ form.as_p }}
            {% if redirect_field_value %}
            <input type="hidden" name="{{ redirect_field_name }}" value="{{ redirect_field_value }}" />
            {% endif %}
            <button class="btn btn-primary" type="submit">{% trans "Sign Up" %} &raquo;</button>
          </form>

          {% get_providers as socialaccount_providers %}
          {% if socialaccount_providers %}
          <hr>
          <div class="socialaccount_ballot">
            <h5 class="mb-3">{% trans "Or sign up with:" %}</h5>
            <div class="socialaccount_providers">
              {% include "socialaccount/snippets/provider_list.html" with process="login" %}
            </div>
          </div>
          {% endif %}
        </div>
      </div>
    </div>
  </div>
</div>
{% endblock %}"""
            
            # Lưu template
            with open(os.path.join(template_dir, 'signup.html'), 'w') as f:
                f.write(signup_template)
            print("Đã tạo template đăng ký mới")

        # Kiểm tra template login
        try:
            template = get_template('account/login.html')
            print("Template đăng nhập đã tồn tại")
        except TemplateDoesNotExist:
            # Tạo template login nếu cần
            import os
            template_dir = os.path.join('templates', 'account')
            os.makedirs(template_dir, exist_ok=True)
            
            login_template = """{% extends "base.html" %}

{% load i18n %}
{% load account socialaccount %}

{% block head_title %}{% trans "Sign In" %}{% endblock %}

{% block content %}
<div class="container mt-5">
  <div class="row justify-content-center">
    <div class="col-md-6">
      <div class="card">
        <div class="card-header bg-primary text-white">
          <h1 class="h4 mb-0">{% trans "Sign In" %}</h1>
        </div>
        <div class="card-body">
          <p>{% blocktrans %}If you have not created an account yet, then please <a href="{{ signup_url }}">sign up</a> first.{% endblocktrans %}</p>

          <form class="login" method="post" action="{% url 'account_login' %}">
            {% csrf_token %}
            {{ form.as_p }}
            {% if redirect_field_value %}
            <input type="hidden" name="{{ redirect_field_name }}" value="{{ redirect_field_value }}" />
            {% endif %}
            <button class="btn btn-primary" type="submit">{% trans "Sign In" %}</button>
            <a class="btn btn-link" href="{% url 'account_reset_password' %}">{% trans "Forgot Password?" %}</a>
          </form>

          {% get_providers as socialaccount_providers %}
          {% if socialaccount_providers %}
          <hr>
          <div class="socialaccount_ballot">
            <h5 class="mb-3">{% trans "Or login with:" %}</h5>
            <div class="socialaccount_providers">
              {% include "socialaccount/snippets/provider_list.html" with process="login" %}
            </div>
          </div>
          {% endif %}
        </div>
      </div>
    </div>
  </div>
</div>
{% endblock %}"""
            
            # Lưu template
            with open(os.path.join(template_dir, 'login.html'), 'w') as f:
                f.write(login_template)
            print("Đã tạo template đăng nhập mới")
            
        # Kiểm tra snippet provider_list
        try:
            template = get_template('socialaccount/snippets/provider_list.html')
            print("Template provider_list đã tồn tại")
        except TemplateDoesNotExist:
            # Tạo thư mục snippets
            import os
            snippet_dir = os.path.join('templates', 'socialaccount', 'snippets')
            os.makedirs(snippet_dir, exist_ok=True)
            
            # Tạo template provider_list
            provider_list_template = """{% load socialaccount %}

{% get_providers as socialaccount_providers %}

{% for provider in socialaccount_providers %}
  {% if provider.id == "openid" %}
    {% for brand in provider.get_brands %}
    <div>
      <a title="{{brand.name}}" 
         class="btn btn-outline-dark mb-2"
         href="{% provider_login_url provider.id openid=brand.openid_url process=process %}">
        <i class="fab fa-{{brand.id}}"></i> {{brand.name}}
      </a>
    </div>
    {% endfor %}
  {% endif %}
  <div>
    <a title="{{provider.name}}" class="btn btn-outline-dark mb-2" 
       href="{% provider_login_url provider.id process=process scope=scope auth_params=auth_params %}">
      {% if provider.id == 'google' %}
        <i class="fab fa-google"></i> Google
      {% elif provider.id == 'facebook' %}
        <i class="fab fa-facebook"></i> Facebook
      {% elif provider.id == 'apple' %}
        <i class="fab fa-apple"></i> Apple
      {% else %}
        {{provider.name}}
      {% endif %}
    </a>
  </div>
{% endfor %}"""

            # Lưu template
            with open(os.path.join(snippet_dir, 'provider_list.html'), 'w') as f:
                f.write(provider_list_template)
            print("Đã tạo template provider_list mới")
            
    except Exception as e:
        print(f"Lỗi khi xử lý templates: {e}")

def fix_duplicate_socialapps():
    """Sửa lỗi nhiều SocialApp cho cùng một provider."""
    print("Đang kiểm tra các SocialApp trùng lặp...")
    
    # Lấy danh sách providers
    providers = SocialApp.objects.values_list('provider', flat=True).distinct()
    
    for provider in providers:
        apps = SocialApp.objects.filter(provider=provider).order_by('-id')
        
        # Nếu có nhiều hơn 1 app cho cùng provider
        if apps.count() > 1:
            print(f"Tìm thấy {apps.count()} SocialApp cho provider '{provider}'")
            
            # Giữ lại app mới nhất, xóa các app cũ
            latest_app = apps.first()
            print(f"Giữ lại app mới nhất (ID: {latest_app.id}, Tên: {latest_app.name})")
            
            # Xóa các app cũ
            for app in apps[1:]:
                print(f"Xóa app cũ (ID: {app.id}, Tên: {app.name})")
                app.delete()
            
            # Đảm bảo app mới được liên kết với tất cả các site
            if latest_app.sites.count() == 0:
                # Nếu không có site nào, thêm site mặc định (id=1)
                try:
                    default_site = Site.objects.get(id=1)
                    latest_app.sites.add(default_site)
                    print(f"Đã thêm site mặc định (ID: 1) cho app")
                except Site.DoesNotExist:
                    print("Site mặc định không tồn tại, đang tạo...")
                    # Tạo site mặc định nếu không tồn tại
                    default_site = Site.objects.create(domain="hoshi.onrender.com", name="Hoshi")
                    latest_app.sites.add(default_site)
                    print(f"Đã tạo và thêm site mặc định cho app")
        else:
            print(f"Không có SocialApp trùng lặp cho provider '{provider}'")
            
            # Kiểm tra xem app có được liên kết với site nào không
            app = apps.first()
            if app and app.sites.count() == 0:
                print(f"App '{app.name}' (ID: {app.id}) không liên kết với site nào, đang thêm site mặc định...")
                try:
                    default_site = Site.objects.get(id=1)
                    app.sites.add(default_site)
                    print(f"Đã thêm site mặc định (ID: 1) cho app")
                except Site.DoesNotExist:
                    print("Site mặc định không tồn tại, đang tạo...")
                    # Tạo site mặc định nếu không tồn tại
                    default_site = Site.objects.create(domain="hoshi.onrender.com", name="Hoshi")
                    app.sites.add(default_site)
                    print(f"Đã tạo và thêm site mặc định cho app")
    
    print("Quá trình kiểm tra và sửa chữa đã hoàn tất!")

# Tạo hoặc cập nhật Site
def ensure_site_exists():
    """Đảm bảo site mặc định tồn tại và được cấu hình đúng."""
    try:
        # Tìm site mặc định (id=1)
        site = Site.objects.get(id=1)
        # Cập nhật tên và domain nếu cần
        if site.domain != "hoshi.onrender.com" or site.name != "Hoshi":
            site.domain = "hoshi.onrender.com"
            site.name = "Hoshi"
            site.save()
            print(f"Đã cập nhật site mặc định (ID: {site.id}): domain={site.domain}, name={site.name}")
        else:
            print(f"Site mặc định đã tồn tại và được cấu hình đúng: domain={site.domain}, name={site.name}")
    except Site.DoesNotExist:
        # Tạo site mặc định nếu không tồn tại
        site = Site.objects.create(id=1, domain="hoshi.onrender.com", name="Hoshi")
        print(f"Đã tạo site mặc định (ID: {site.id}): domain={site.domain}, name={site.name}")
    
    # Kiểm tra và xóa các site dư thừa
    extra_sites = Site.objects.exclude(id=1)
    if extra_sites.exists():
        count = extra_sites.count()
        extra_sites.delete()
        print(f"Đã xóa {count} site dư thừa")

# Hiển thị thông tin về SocialApp
def display_socialapps():
    """Hiển thị thông tin về các SocialApp."""
    apps = SocialApp.objects.all()
    print(f"\nDanh sách SocialApp ({apps.count()}):")
    for app in apps:
        sites = app.sites.all()
        site_names = ", ".join([site.domain for site in sites])
        print(f"- ID: {app.id}, Provider: {app.provider}, Tên: {app.name}, Client ID: {app.client_id}")
        print(f"  Sites: {site_names}")

# Patch SocialAccountAdapter để xử lý lỗi MultipleObjectsReturned
def patch_socialaccount_adapter():
    from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
    
    # Lưu reference đến phương thức gốc
    original_get_app = DefaultSocialAccountAdapter.get_app
    
    def patched_get_app(self, request, provider):
        try:
            return original_get_app(self, request, provider)
        except MultipleObjectsReturned:
            print(f"Đã phát hiện lỗi MultipleObjectsReturned cho provider {provider}, đang sửa chữa...")
            fix_duplicate_socialapps()
            
            # Lấy app mới nhất sau khi đã sửa chữa
            from allauth.socialaccount.models import SocialApp
            app = SocialApp.objects.filter(provider=provider).order_by('-id').first()
            if app is None:
                raise Exception(f"Không tìm thấy SocialApp cho provider {provider}")
            return app
    
    # Áp dụng patch
    DefaultSocialAccountAdapter.get_app = patched_get_app
    print("Đã patch DefaultSocialAccountAdapter.get_app để xử lý lỗi MultipleObjectsReturned")

if __name__ == "__main__":
    print("=== Bắt đầu sửa chữa cấu hình SocialApp ===")
    
    # Đảm bảo site mặc định tồn tại
    ensure_site_exists()
    
    # Sửa lỗi SocialApp trùng lặp
    fix_duplicate_socialapps()
    
    # Patch adapter để xử lý lỗi MultipleObjectsReturned
    patch_socialaccount_adapter()
    
    # Kiểm tra và sửa templates
    fix_signup_template()
    
    # Hiển thị thông tin sau khi sửa chữa
    display_socialapps()
    
    print("\n=== Quá trình sửa chữa đã hoàn tất ===")