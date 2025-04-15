from django.urls import path
from . import views
from . import api

app_name = 'posts'

urlpatterns = [
    path('', views.index, name='index'),
    path('create/', views.create, name='create'),
    path('<int:post_id>/', views.post_detail, name='post_detail'),
    path('<int:post_id>/edit/', api.edit_post, name='edit'),
    path('<int:post_id>/delete/', api.delete_post, name='delete'),
    path('<int:post_id>/like/', views.like_post, name='like'),
    path('<int:post_id>/save/', views.save_post, name='save'),
    path('<int:post_id>/comment/', views.add_comment, name='comment'),
    path('<int:post_id>/comment/<int:comment_id>/delete/', views.delete_comment, name='comment_delete'),
    path('comments/<int:comment_id>/like/', views.like_comment, name='like_comment'),
    path('explore/', views.explore, name='explore'),
    path('saved/', views.saved_posts, name='saved'),
    path('liked/', views.liked_posts, name='liked_posts'),
    path('<int:post_id>/report/', views.report_post, name='report_post'),
    path('<int:post_id>/likes/', views.get_post_likes, name='post_likes'),
    path('search/', views.search, name='search'),
    # API endpoints
    path('api/comments/add/', views.api_add_comment, name='api_add_comment'),
    path('api/posts/load/', views.api_load_posts, name='api_load_posts'),
    # Endpoints mới cho gợi ý hashtag và người dùng
    path('api/hashtag-suggestions/', api.hashtag_suggestions, name='hashtag_suggestions'),
    path('api/user-suggestions/', api.user_suggestions, name='user_suggestions'),
    # Endpoint chia sẻ bài viết
    path('share/', api.share_post, name='share_post'),
    # Report URLs
    path('<int:post_id>/report-modal/', views.report_post_modal, name='report_post_modal'),
    path('<int:post_id>/report-ajax/', views.report_post_ajax, name='report_post_ajax'),
] 