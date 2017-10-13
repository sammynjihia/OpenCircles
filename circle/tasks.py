from __future__ import absolute_import, unicode_literals
from celery import shared_task
from app_utility import circle_utils
from circle.models import CircleInvitation
import json



@shared_task
def send_circle_invites(id_list):
    circle_invitations = CircleInvitation.objects.filter(id__in = id_list)
    instance = circle_utils.Circle()
    print ("Started celery task")

    try:
        instance.send_circle_invitation(circle_invitations)

    except Exception as e:
        print(e)

    message = "Saved contacts successfully"

    print ("Celery task completed successfully")

    with open('celery_save_contacts_worker_file.txt', 'a') as post_file:
        post_file.write(str(circle_invitations))
        post_file.write("\n")


    return message