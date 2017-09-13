from pyfcm import FCMNotification
from decouple import config

class Fcm():
    def notification_push(self,device,registration_id,message_title,message_body):
        push_service = FCMNotification(api_key=config('SERVER_KEY'))
        # proxy_dic = {"http":"http://192.168.0.12","https":"https://192.168.0.12"}
        if device == "single":
            result = push_service.notify_single_device(registration_id=registration_id,message_title=message_title,message_body=message_body)
        else:
            result = push_service.notify_mutiple_device(registration_id=registration_id,message_title=message_title,message_body=message_body)
        print result

    def data_push(self,device,registration_id,data_message):
        push_service = FCMNotification(api_key=config('SERVER_KEY'))
        if device == "single":
            result = push_service.notify_single_device(registration_id=registration_id,data_message=data_message)
        else:
            result = push_service.notify_mutiple_device(registration_id=registration_id,data_message=data_message)
        print result
