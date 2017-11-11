# Create your tasks here
from __future__ import absolute_import, unicode_literals
from celery import shared_task
from member.models import Contacts
from app_utility import sms_utils, loan_utils, circle_utils


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
    contacts_to_sent = invite_contacts.order_by('phone_number').values_list('phone_number', flat=True).distinct()
    numbers = ','.join(contacts_to_sent)
    sms = sms_utils.Sms()
    message = "Break Bounderies and explore discovered opportunities with the all new OpenCircles mobile app. A revolutionary way to invest your money. Join now" \
              " and find out why mobile financing will never be the same again. "
    if invite_contacts.exists():
        # response,unsent = sms.sendmultiplesms(numbers, message)
        if response:
            invite_contacts.exclude(phone_number__in=unsent).update(invitation_sent=True)
    else:
        print("No contacts in this table")

    loans = loan_utils.Loan()
    #send loan reminders from this function
    loans.loan_repayment_reminder()

    #Delete loans that have expired I.E have exceeded the 1 week time span without all the guarantors accepting
    loans.delete_expired_loan()

    circle_member = circle_utils.Circle()
    circle_member.deactivate_circle_member()

    #Don't use the below
    invitees = invite_contacts.count()
    list_of_numbers = ['254712388212', '254714642293', '254713189107']

    log_message = "{} contacts will receive a message in production mode".format(invitees)
    return log_message
