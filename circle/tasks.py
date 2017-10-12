from __future__ import absolute_import, unicode_literals
from celery import shared_task
from app_utility import circle_utils
from member.models import Member
import json



@shared_task
def send_circle_invites(circle_invitations):
    instance = circle_utils.Circle()
    circle_invitations = json.loads(circle_invitations)
    instance.send_circle_invitation(circle_invitations)
    message = "Saved contacts successfully"

    with open('celery_save_contacts_worker_file.txt', 'a') as post_file:
        post_file.write(str(circle_invitations))
        post_file.write("\n")


    return message