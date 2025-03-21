from django.urls import path, include
from rest_framework_nested import routers
from . import api

router = routers.DefaultRouter()
router.register(r'', api.PostViewSet, basename='post')
router.register(r'hashtags', api.HashtagViewSet, basename='hashtag')

posts_router = routers.NestedDefaultRouter(router, r'', lookup='post')
posts_router.register(r'comments', api.CommentViewSet, basename='post-comments')

app_name = 'posts-api'

urlpatterns = [
    path('', include(router.urls)),
    path('', include(posts_router.urls)),
    path('list/', api.post_list, name='post_list'),
    path('<int:pk>/', api.post_detail, name='post_detail'),
    path('<int:pk>/like/', api.like_post, name='like_post'),
    path('<int:pk>/save/', api.save_post, name='save_post'),
    path('<int:pk>/comments/', api.comment_list, name='comment_list'),
    path('comments/add/', api.add_comment, name='add_comment'),
    path('comments/<int:pk>/delete/', api.delete_comment, name='delete_comment'),
    path('comments/<int:pk>/like/', api.like_comment, name='like_comment'),
] 