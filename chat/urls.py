from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include

from chat.views import *
from chat_backend import settings

urlpatterns = [
    path('chat', ChatView.as_view(), name='chat'),
    path('chat/<int:chat_id>/members', MemberView.as_view(), name='members'),
    path('chat/<int:chat_id>/messages/', GetMessagesView.as_view(), name='members'),
    path('chats', GetAllUserChatView.as_view(), name='members'),
    path('media', UploadMedia.as_view(), name='media')
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)