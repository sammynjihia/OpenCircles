from africastalking.AfricasTalkingGateway import (AfricasTalkingGateway, AfricasTalkingGatewayException)
class Sms:
    def __init__(self):
        self.username = "SAMMIENJIHIA"
        self.api_key = "9898e481449e39a6051b3d87e07f4de171bedc93a046dd166c0dad2d0d9b6bdc"
    def format_phone_number(self,phone_number):
        to = ''
        phone_number = str(phone_number).replace(" ","")
        if phone_number[0: 4] == '+254':
            to = phone_number
        elif phone_number[0: 4] == '2547':
            to = '+' + str(phone_number)
        elif phone_number[0: 2] == '07':
            to = '+254' + phone_number[1: ]
        elif phone_number[0: 1] == '7':
            to = '+254' + phone_number
        return to
    def sendsms(self,to,message):
        to = self.format_phone_number(to)
        gateway = AfricasTalkingGateway(self.username,self.api_key)
        try:
            response = gateway.sendMessage(to,message)
            if response[0]['status'] == 'Success':
                return True
            else:
                return False
        except Exception as e:
            return False

    def sendmultiplesms(self,to,message):
        gateway = AfricasTalkingGateway(self.username, self.api_key)
        try:
            response = gateway.sendMessage(to,message)
            unsent = [res['number'] for res in response if res['status'] != 'Success']
            return True,unsent
        except Exception as e:
            return False,''
