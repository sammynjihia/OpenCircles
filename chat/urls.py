from django.conf.urls import url
from .views import *

urlpatterns = [
    url(r'^send_chat/$', save_chat,name="send-chat"),
    url(r'^retrieve_chats/$', retrieve_chat, name="retrieve-chat")
]
