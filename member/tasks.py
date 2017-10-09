# Create your tasks here
from __future__ import absolute_import, unicode_literals
from celery import shared_task
from member.models import Contacts
from app_utility import sms_utils


@shared_task
def add(x, y):
    return x + y


@shared_task
def mul(x, y):
    return x * y


@shared_task
def xsum(numbers):
    return sum(numbers)


@shared_task
def send_frequent_invitations():
    invite_contacts = Contacts.objects.filter(is_member=False, is_valid=True, invitation_sent=False)
    sms = sms_utils.Sms()
    message = "Break Bounderies and explore discovered opportunities with the all new OpenCircles mobile app. A revolutionary way to invest your money. Join now" \
              " and find out why mobile financing will never be the same again. "
    invitees = invite_contacts.count()
    list_of_numbers = ['254712388212', '254714642293', '254713189107']
    for number in list_of_numbers:
        sms.sendsms(to=number, message=message)

    if invite_contacts.exists():
        for contacts in invite_contacts:
            to = contacts.phone_number
            #sms.sendsms(to=to, message=message)
            contacts.invitation_sent=True
            contacts.save()
    else:
        print("No contacts in this table")

    log_message = "{} contacts will receive a message in production mode".format(invitees)
    return log_message