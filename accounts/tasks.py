from __future__ import absolute_import, unicode_literals
from celery import shared_task
from app_utility import accounts_utils
from member.models import Member



@shared_task
def save_member_contacts(user,contacts):
    instance = accounts_utils.Account()
    user = Member.objects.get(id=user)
    instance.save_contacts(user, contacts)
    message = "Saved contacts successfully"

    with open('celery_save_contacts_worker_file.txt', 'a') as post_file:
        post_file.write(user)
        post_file.write("\n")
        post_file.write(contacts)
        post_file.write("\n")

    return message