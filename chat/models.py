from __future__ import unicode_literals

from django.db import models

from member.models import Member
from app_admin.models import AppAdmin


# Create your models here.
class Chat(models.Model):
    owner = models.ForeignKey(Member, null=False, on_delete=models.CASCADE)
    responded_to_by = models.ForeignKey(AppAdmin, null=True, on_delete=models.SET_NULL)
    sender = models.CharField(max_length=15, default="SELF")
    recipient = models.CharField(max_length=15, default="SELF")
    body = models.TextField()
    time_chat_sent = models.DateTimeField(auto_now_add=True)
    has_been_responded_to = models.BooleanField(default=False)
    is_cancelled = models.BooleanField(default=False)

    class Meta:
        db_table = "Chat"
