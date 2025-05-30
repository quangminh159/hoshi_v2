<!DOCTYPE html>
{% load static %}
{% load i18n %}
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}Hoshi - Mạng xã hội chia sẻ khoảnh khắc{% endblock %}</title>
    
    <!-- Favicon -->
    <link rel="shortcut icon" href="{% static 'img/favicon.ico' %}" type="image/x-icon">
    
    <!-- Bootstrap CSS -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    
    <!-- Font Awesome -->
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    
    <!-- Custom CSS -->
    <link href="{% static 'css/style.css' %}" rel="stylesheet">
    
    <!-- Thêm CSS để ẩn thông báo -->
    <link rel="stylesheet" href="{% static 'css/hide_notifications.css' %}">
    
    {% if user.is_authenticated %}
    <meta name="user-id" content="{{ user.id }}">
    {% endif %}
    
    {% block extra_css %}{% endblock %}
</head>
<body class="bg-light">
    <!-- Navbar -->
    <nav class="navbar navbar-expand-lg navbar-light bg-white border-bottom fixed-top">
        <div class="container">
            <a class="navbar-brand" href="{% url 'home' %}">
                <img src="{% static 'img/logo.png' %}" alt="Hoshi" height="30">
            </a>
            
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
                <span class="navbar-toggler-icon"></span>
            </button>
            
            <div class="collapse navbar-collapse" id="navbarNav">
                <form class="d-flex mx-auto" action="{% url 'posts:search' %}" method="get">
                    <div class="input-group">
                        <input type="search" class="form-control" name="q" placeholder="Tìm kiếm...">
                        <button class="btn btn-outline-secondary" type="submit">
                            <i class="fas fa-search"></i>
                        </button>
                    </div>
                </form>
                
                <ul class="navbar-nav ms-auto">
                    {% if user.is_authenticated %}
                        <li class="nav-item">
                            <a class="nav-link" href="{% url 'home' %}">
                                <i class="fas fa-home"></i>
                            </a>
                        </li>
                        <li class="nav-item">
                            <a class="nav-link" href="{% url 'chat:conversation_list' %}">
                                <i class="fas fa-paper-plane"></i>
                            </a>
                        </li>
                        <li class="nav-item">
                            <a class="nav-link" href="{% url 'posts:create' %}">
                                <i class="fas fa-plus-square"></i>
                            </a>
                        </li>
                        <li class="nav-item">
                            <a class="nav-link" href="{% url 'posts:explore' %}">
                                <i class="fas fa-compass"></i>
                            </a>
                        </li>
                        <li class="nav-item">
                            <a class="nav-link position-relative" href="{% url 'notifications:list' %}">
                                <i class="fas fa-heart"></i>
                                {% if unread_notifications_count %}
                                    <span class="position-absolute top-0 start-100 translate-middle badge rounded-pill bg-danger">
                                        {{ unread_notifications_count }}
                                    </span>
                                {% endif %}
                            </a>
                        </li>
                        <li class="nav-item dropdown">
                            <a class="nav-link dropdown-toggle" href="#" id="navbarDropdown" role="button" data-bs-toggle="dropdown">
                                {% if user.get_avatar_url %}
                                    <img src="{{ user.get_avatar_url }}" 
                                         alt="{{ user.username }}" 
                                         class="rounded-circle"
                                         width="24" 
                                         height="24">
                                {% else %}
                                    <img src="{% static 'img/default-avatar.png' %}" 
                                         alt="{{ user.username }}" 
                                         class="rounded-circle"
                                         width="24" 
                                         height="24">
                                {% endif %}
                            </a>
                            <ul class="dropdown-menu dropdown-menu-end">
                                <li>
                                    <a class="dropdown-item" href="{% url 'accounts:profile' user.username %}">
                                        <i class="fas fa-user me-2"></i>Trang cá nhân
                                    </a>
                                </li>
                                <li>
                                    <a class="dropdown-item" href="{% url 'posts:saved' %}">
                                        <i class="fas fa-bookmark me-2"></i>Đã lưu
                                    </a>
                                </li>
                                <li>
                                    <a class="dropdown-item" href="{% url 'accounts:settings' %}">
                                        <i class="fas fa-cog me-2"></i>Cài đặt
                                    </a>
                                </li>
                                <li><hr class="dropdown-divider"></li>
                                <li>
                                    <a class="dropdown-item" href="{% url 'account_logout' %}">
                                        <i class="fas fa-sign-out-alt me-2"></i>Đăng xuất
                                    </a>
                                </li>
                            </ul>
                        </li>
                    {% else %}
                        <li class="nav-item">
                            <a class="nav-link" href="{% url 'account_login' %}">Đăng nhập</a>
                        </li>
                        <li class="nav-item">
                            <a class="nav-link" href="{% url 'account_signup' %}">Đăng ký</a>
                        </li>
                    {% endif %}
                </ul>
            </div>
        </div>
    </nav>
    
    <!-- Main Content -->
    <main class="container py-5 mt-5">
        {% if messages %}
            {% for message in messages %}
                <div class="alert alert-{{ message.tags }} alert-dismissible fade show" role="alert">
                    {{ message }}
                    <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                </div>
            {% endfor %}
        {% endif %}
        
        {% block content %}{% endblock %}
    </main>
    
    <!-- Bootstrap Bundle with Popper -->
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    
    <!-- jQuery -->
    <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
    
    <!-- Custom JS -->
    <script src="{% static 'js/main.js' %}"></script>
    <script src="{% static 'js/debug_feed.js' %}"></script>
    <script src="{% static 'js/disable_multiple_submissions.js' %}"></script>
    
    {% block extra_js %}{% endblock %}

</body>
</html> 