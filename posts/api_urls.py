from django.urls import path, include
from rest_framework_nested import routers
from . import api
from . import views

router = routers.DefaultRouter()
router.register(r'posts', api.PostViewSet, basename='post')
router.register(r'hashtags', api.HashtagViewSet, basename='hashtag')

posts_router = routers.NestedDefaultRouter(router, r'posts', lookup='post')
posts_router.register(r'comments', api.CommentViewSet, basename='post-comments')

app_name = 'posts-api'

urlpatterns = [
    path('', api.post_list, name='post_list'),
    path('list/', api.post_list, name='post_list'),
    path('', include(router.urls)),
    path('', include(posts_router.urls)),
    path('<int:pk>/', api.post_detail, name='post_detail'),
    path('<int:pk>/like/', api.like_post, name='like_post'),
    path('<int:pk>/save/', api.save_post, name='save_post'),
    path('<int:pk>/comments/', api.comment_list, name='comment_list'),
    path('posts/<int:pk>/', api.post_detail, name='post_detail_new'),
    path('posts/<int:pk>/like/', api.like_post, name='like_post_new'),
    path('posts/<int:pk>/save/', api.save_post, name='save_post_new'),
    path('posts/<int:pk>/comments/', api.comment_list, name='comment_list_new'),
    path('comments/add/', api.add_comment, name='add_comment'),
    path('comments/<int:pk>/delete/', api.delete_comment, name='delete_comment'),
    path('comments/<int:pk>/like/', api.like_comment, name='like_comment'),
    path('track-interaction/', api.track_interaction, name='track_interaction'),
    path('hashtag-suggestions/', api.hashtag_suggestions, name='hashtag_suggestions'),
    path('user-suggestions/', api.user_suggestions, name='user_suggestions'),
] 