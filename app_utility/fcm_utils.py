from pyfcm import FCMNotification

class Fcm():
    def push(self,registration_id,message_title,message_body):
        push_service = FCMNotification(api_key="AAAA2sfv3GA:APA91bGcjUqiiS5_rpzqkVp1IrOzwdHUxDycernJ5629zbTS4BrpE3kwoVwu0NSpi6-2sP95L9ErDd-78j-92RIod5aO7xoLAcSo6-rXk4c85YbAFEJCGEumYAeVToLx4TBWdoMvtuc3")
        # proxy_dic = {"http":"http://192.168.0.12","https":"https://192.168.0.12"}
        result = push_service.notify_single_device(registration_id=registration_id,message_title=message_title,message_body=message_body)
        print result
