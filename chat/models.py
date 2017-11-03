from __future__ import unicode_literals

from django.db import models

from member.models import Member

# Create your models here.
class Chat(models.Model):
    owner = models.ForeignKey(Member, null=False, on_delete=models.CASCADE)
    sender = models.CharField(max_length=15,default="SELF")
    recipient = models.CharField(max_length=15,default="SELF")
    body = models.TextField()
    time_chat_sent = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "Chat"
