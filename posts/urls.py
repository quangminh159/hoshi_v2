from django.urls import path
from . import views

app_name = 'posts'

urlpatterns = [
    path('', views.home, name='home'),
    path('feed/', views.feed, name='feed'),
    path('create/', views.create_post, name='create'),
    path('<int:post_id>/', views.post_detail, name='post_detail'),
    path('<int:post_id>/edit/', views.edit_post, name='edit'),
    path('<int:post_id>/delete/', views.delete_post, name='delete'),
    path('<int:post_id>/like/', views.like_post, name='like'),
    path('<int:post_id>/save/', views.save_post, name='save'),
    path('<int:post_id>/comment/', views.add_comment, name='comment'),
    path('<int:post_id>/comment/<int:comment_id>/delete/', views.delete_comment, name='comment_delete'),
    path('comments/<int:comment_id>/like/', views.like_comment, name='like_comment'),
    path('explore/', views.explore, name='explore'),
    path('saved/', views.saved_posts, name='saved'),
    path('<int:post_id>/report/', views.report_post, name='report'),
    path('<int:post_id>/likes/', views.get_post_likes, name='post_likes'),
    path('search/', views.search, name='search'),
    # API endpoints
    path('api/comments/add/', views.api_add_comment, name='api_add_comment'),
    path('api/posts/load/', views.api_load_posts, name='api_load_posts'),
] 