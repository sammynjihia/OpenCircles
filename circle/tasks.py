from __future__ import absolute_import, unicode_literals
from celery import shared_task
from app_utility import circle_utils
from circle.models import CircleInvitation
import json



@shared_task
def send_circle_invites(id_list):
    circle_invitations = CircleInvitation.objects.filter(id__in = id_list)
    instance = circle_utils.Circle()
    instance.send_circle_invitation(circle_invitations)
    message = "Saved contacts successfully"
    return message