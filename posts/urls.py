from django.urls import path
from django.shortcuts import redirect
from . import views
from . import api

app_name = 'posts'


def redirect_explore_to_search(request):
    """URL /posts/explore/ cũ → chuyển sang tìm kiếm."""
    tag = request.GET.get('tag') or request.GET.get('q') or ''
    if tag:
        return redirect(f'/posts/search/?q={tag}')
    return redirect('posts:search')


urlpatterns = [
    path('', views.index, name='index'),
    path('create/', views.create, name='create'),
    path('<int:post_id>/feed-comments/', views.feed_comments_json, name='feed_comments'),
    path('comments/<int:comment_id>/feed-replies/', views.feed_comment_replies_json, name='feed_comment_replies'),
    path('<int:post_id>/', views.post_detail, name='post_detail'),
    path('<int:post_id>/edit/', api.edit_post, name='edit'),
    path('<int:post_id>/delete/', api.delete_post, name='delete'),
    path('<int:post_id>/like/', views.like_post, name='like'),
    path('<int:post_id>/save/', views.save_post, name='save'),
    path('<int:post_id>/comment/', views.add_comment, name='comment'),
    path('<int:post_id>/comment/<int:comment_id>/delete/', views.delete_comment, name='comment_delete'),
    path('comments/<int:comment_id>/like/', views.like_comment, name='like_comment'),
    path('saved/', views.saved_posts, name='saved'),
    path('liked/', views.liked_posts, name='liked_posts'),
    path('<int:post_id>/report/', views.report_post, name='report_post'),
    path('<int:post_id>/likes/', views.get_post_likes, name='post_likes'),
    path('search/', views.search, name='search'),
    path('location/', views.location_detail, name='location'),
    path('explore/', redirect_explore_to_search, name='explore'),
    path('api/comments/add/', views.api_add_comment, name='api_add_comment'),
    path('api/posts/load/', views.api_load_posts, name='api_load_posts'),
    path('api/posts/impressions/', views.track_impressions, name='track_impressions'),
    path('api/hashtag-suggestions/', api.hashtag_suggestions, name='hashtag_suggestions'),
    path('api/user-suggestions/', api.user_suggestions, name='user_suggestions'),
    path('api/search-suggestions/', api.search_suggestions, name='search_suggestions'),
    path('api/location-suggestions/', api.location_suggestions, name='location_suggestions'),
    path('api/reverse-geocode/', api.reverse_geocode, name='reverse_geocode'),
    path('share/', api.share_post, name='share_post'),
    path('share/recipients/', api.share_message_recipients, name='share_message_recipients'),
    path('share/via-message/', api.share_post_via_message, name='share_post_via_message'),
    path('<int:post_id>/report-modal/', views.report_post_modal, name='report_post_modal'),
    path('<int:post_id>/report-ajax/', views.report_post_ajax, name='report_post_ajax'),
]
