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
    contacts_to_send = contacts_to_sent[:500]
    numbers = ','.join(contacts_to_send)
    numbers = numbers.encode("ascii")
    sms = sms_utils.Sms()
    message = "Opencircles is a platform where friends, family and colleagues can pull resources to save and invest" \
              " in consumer credit. Create a circle and get your whatsapp group to join and save in the circle and" \
              " stand a chance to win Kes 5,000 every friday this festive season." \
              " Get the app on play store at https://goo.gl/5KWXhx"
    if invite_contacts.exists():
        # response,unsent = sms.sendmultiplesms(numbers, message)
        # if response:
        #     invite_contacts.exclude(phone_number__in=unsent).update(invitation_sent=True)
        pass
    else:
        print("No contacts in this table")

    loans = loan_utils.Loan()
    #send loan reminders from this function
    loans.loan_repayment_reminder()

    #Delete loans that have expired I.E have exceeded the 1 week time span without all the guarantors accepting
    loans.delete_expired_loan()

    circle_instance = circle_utils.Circle()
    circle_instance.deactivate_circle_member()
    circle_instance.delete_inactive_circles()
    return "Sent messages successfully"
