from __future__ import absolute_import, unicode_literals
from celery import shared_task
from app_utility import accounts_utils
from member.models import Member
from app_admin import chat_utils



@shared_task
def save_member_contacts(user,contacts):
    instance = accounts_utils.Account()
    user = Member.objects.get(id=user)
    instance.save_contacts(user, contacts)
    message = "Saved contacts successfully"

    with open('celery_save_contacts_worker_file.txt', 'a') as post_file:
        post_file.write(str(user))
        post_file.write("\n")
        post_file.write(str(contacts))
        post_file.write("\n")

    return message


@shared_task
def send_welcome_message1(user):
    member = Member.objects.get(id=user)
    message = "Hi there, Welcome to Opencircles, a peer-to-peer savings and credit platform that helps you access affordable credit and earn interest from your savings. With Opencircles, you can save, borrow and transfer funds among your social circles. With your Opencircles wallet, you can transfer cash to another Opencircles wallet all for free. You can also pay for goods and services and send cash to an m-pesa number or even a bank account. Remember, your savings earn interest from loans repaid. We are glad to have you on board."
    chat_utils.ChatUtils.send_single_chat(message, member, 1)

    success_mesage = "Sent welcome message successfully"
    return success_mesage


@shared_task
def send_welcome_message2(user):
    member = Member.objects.get(id=user)
    message = "What next after registering with Opencircles? For an improved experience, you can join or create a circle and invite your friends, family and colleagues to join and start saving in that circle. Membership to a circle allows you to borrow at affordable rates and earn interest on your savings from the loans repaid in that circle."
    chat_utils.ChatUtils.send_single_chat(message, member, 1)

    success_mesage = "Sent welcome message successfully"
    return success_mesage


@shared_task
def send_welcome_message3(user):
    member = Member.objects.get(id=user)
    message = "Joining a circle is simple, just click on any recommended or invited circle, and tap on the join circle button. It is highly recommended to join a circle that has atleast one member from you contacts."
    chat_utils.ChatUtils.send_single_chat(message, member, 1)

    success_mesage = "Sent welcome message successfully"
    return success_mesage

@shared_task
def send_welcome_message4(user):
    member = Member.objects.get(id=user)
    message = "If you would like to create your own circle, just tap on the create new circle icon, select the circle type, either private or open, members can join a private circle strictly by invitation only while anyone can join an open circle. Add a name for your circle and the initial deposit that you would like your members to join at, should be atleast Ksh 50. Next, add the interest rates that you would like your members to borrow at, the loan interest rates should be between 3% to 15%, then invite members to your circle. A circle shall only be activated if atleast five members join"
    chat_utils.ChatUtils.send_single_chat(message, member, 1)

    success_mesage = "Sent welcome message successfully"
    return success_mesage