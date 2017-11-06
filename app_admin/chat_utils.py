
from chat.models import Chat
from member.models import Member
from django.db.models import Q
from app_utility import fcm_utils, sms_utils
import datetime


class ChatUtils:
    @staticmethod
    def get_pending_chats():
        return Chat.objects.filter(has_been_responded_to=False).order_by('-time_chat_sent')


    @staticmethod
    def search_for_chats(search_val):
        if len(search_val.strip()) ==0:
            return
        sms = sms_utils.Sms()
        chat_objs = Chat.objects.filter(Q(Q(body__icontains=search_val) |
                                          Q(owner=Member.objects
                                            .filter(Q(Q(phone_number=sms.format_phone_number(search_val))
                                                      |Q(national_id=search_val))))), recipient__icontains='opencircles')
        return chat_objs


    @staticmethod
    def reply_to_chat(chat_id, body):
        body = body.strip()
        if len(body) == 0:
            return False

        in_reply_to_chat = Chat.objects.get(id=chat_id)
        member = in_reply_to_chat.owner
        try:
            Chat(sender='Opencircles', recipient='SELF', body=body, owner=member,
                        time_chat_sent=datetime.datetime.now(), has_been_responded_to=True).save()
            in_reply_to_chat.has_been_responded_to = True
            in_reply_to_chat.save()

            instance = fcm_utils.Fcm()
            registration_id = member.device_token

            fcm_data = {
                'request_type': 'REPLY_TO_CHAT',
                'sender': 'Opencircles',
                'body': body,
                'time_sent': datetime.datetime.now().strftime('%Y-%m-%d %H-%m-%s')
                }
            instance.data_push("single", registration_id, fcm_data)
            return True
        except Exception as exp:
            print(exp)
            return False






