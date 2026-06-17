from django.urls import path
from . import views
from . import chat_views

app_name = 'webapp'

urlpatterns = [
    path('', views.home, name='home'),
    path('chapter/<slug:slug>/', views.chapter, name='chapter'),
    # Chat API
    path('api/chat/stream', chat_views.api_message_stream, name='api_message_stream'),
    path('api/chat/clear',  chat_views.api_clear_chat,    name='api_clear_chat'),
]
