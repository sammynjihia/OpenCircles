from __future__ import absolute_import, unicode_literals
from celery import shared_task
from app_utility import accounts_utils



@shared_task
def save_member_contacts(user,contacts):
    instance = accounts_utils.Account()
    instance.save_contacts(user, contacts)
    message = "Saved contacts successfully"

    with open('celery_save_contacts_worker_file.txt', 'a') as post_file:
        post_file.write(message)
        post_file.write("\n")

    return message