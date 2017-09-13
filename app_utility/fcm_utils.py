from pyfcm import FCMNotification

class Fcm():
    def push(self,registration_id,message_title,message_body):
        push_service = FCMNotification(api_key="AAAAGecML_c:APA91bHeL8J7Egizw4NExLX8Ooh2z_MaIMjbieUm4K7eYspF0pvntY2ny2C_UqMQYUclrwvILQ-OoXJ--r3atjGqMW2Tck5UE88NOfMkxPyvxfmkaMuVkM8PnwV0sQ087t2PIaqJZfdy")
        # proxy_dic = {"http":"http://192.168.0.12","https":"https://192.168.0.12"}
        result = push_service.notify_single_device(registration_id=registration_id,message_title=message_title,message_body=message_body)
        print result
