from africastalking.AfricasTalkingGateway import (AfricasTalkingGateway, AfricasTalkingGatewayException)
class Sms:
    def __init__(self):
        self._username = "SAMMIENJIHIA"
        self._api_key = "9898e481449e39a6051b3d87e07f4de171bedc93a046dd166c0dad2d0d9b6bdc"
        self._gateway = AfricasTalkingGateway(self._username, self._api_key)

    def format_phone_number(self, phone_number):
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

    def format_amount(self, amount):
        initial = "KES "
        amount = initial + str(amount)
        return amount

    def sendsms(self, to, message):
        to = self.format_phone_number(to)

        try:
            sender = "FLEMISHLTD"
            response = self._gateway.sendMessage(to, message, sender)
            print(response)
            if response[0]['status'] == 'Success':
                return True
            else:
                return False
        except Exception as e:
            print(str(e))
            return False

    def sendmultiplesms(self, to, message):
        try:
            sender = "FLEMISHLTD"
            response = self._gateway.sendMessage(to, message, sender)
            unsent = [res['number'] for res in response if res['status'] != 'Success']
            return True,unsent
        except Exception as e:
            return False,''

    def buyairtime(self, phone_number, amount):
        phone_number, amount = self.format_phone_number(phone_number), self.format_amount(amount)
        recipient = [{"phoneNumber":phone_number, "amount":amount}]
        try:
            response = self._gateway.sendAirtime(recipient)
            print(response)
            if response[0]['status'] == 'Success' or response[0]['status'] == 'Sent':
                return True
            else:
                return False

        except AfricasTalkingGatewayException as e:
            print(str(e))
            return False