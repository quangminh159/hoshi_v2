from django.urls import path
from . import views

app_name = 'chat'

urlpatterns = [
    path('', views.room_list, name='room_list'),
    path('<int:room_id>/', views.room_detail, name='room_detail'),
    path('create/', views.create_room, name='create_room'),
    path('<int:room_id>/send/', views.send_message, name='send_message'),
] 