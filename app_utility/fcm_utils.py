from pyfcm import FCMNotification
from decouple import config

from circle.models import CircleMember,CircleInvitation
from member.models import Member

class Fcm():
    def notification_push(self,device,registration_id,message_title,message_body):
        push_service = FCMNotification(api_key=config('SERVER_KEY'))
        # proxy_dic = {"http":"http://192.168.0.12","https":"https://192.168.0.12"}
        if device == "single":
            result = push_service.notify_single_device(registration_id=registration_id,message_title=message_title,message_body=message_body)
        else:
            result = push_service.notify_multiple_devices(registration_ids=registration_id,message_title=message_title,message_body=message_body)
        print(result)

    def data_push(self,device,registration_id,data_message):
        push_service = FCMNotification(api_key=config('SERVER_KEY'))
        if device == "single":
            result = push_service.notify_single_device(registration_id=registration_id,data_message=data_message)
        else:
            result = push_service.notify_multiple_devices(registration_ids=registration_id,data_message=data_message)
        print(result)

    def get_circle_members_token(self,circle,member):
        if member is None:
            circle_members = CircleMember.objects.filter(circle=circle)
        else:
            circle_members = CircleMember.objects.filter(circle=circle).exclude(member=member)
        registration_ids= [cm.member.device_token for cm in circle_members]
        return registration_ids

    def get_invited_circle_member_token(self,circle,member):
        circle_member = CircleMember.objects.get(circle=circle,member=member)
        invited_members = Member.objects.filter(phone_number__in = CircleInvitation.objects.filter(invited_by=circle_member,is_member=True).values_list('phone_number',flat=True))
        registration_ids = [im.device_token for im in invited_members]
        return registration_ids
