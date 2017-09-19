import requests
import json
from requests.auth import HTTPBasicAuth
import datetime
import base64

consumer_key = "tAEyfavNAtEi68QLD7j534XgVCYQkY1v"
consumer_secret = "S7IQHLdo2epsV35O"
api_URL = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
main_url = "https://fgehbulqxm.localtunnel.me/"
lipaonline_callbackURL = main_url + "wallet/mpesaCallbackURL/"
shortcode = "174379"
timestamp_raw = datetime.datetime.now()
timestamp = timestamp_raw.strftime('%Y%m%d%I%M%S')
passkey = "bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919"
password_raw = bytes(shortcode + passkey + timestamp)
password = base64.b64encode(password_raw )



class MpesaUtils():
    def get_access_token(self):
        r = requests.get(api_URL, auth=HTTPBasicAuth(consumer_key, consumer_secret))
        mpesa_reponse = json.loads(r.text)
        access_token = mpesa_reponse['access_token']
        return access_token

    def mpesa_online_checkout(self, amount, phone_number):
        access_token = self.get_access_token()
        api_url = "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest"
        headers = { "Authorization": "Bearer %s" % access_token }
        request = {
          "BusinessShortCode": shortcode,
          "Password": password,
          "Timestamp": timestamp,
          "TransactionType": "CustomerPayBillOnline",
          "Amount": amount,
          "PartyA": phone_number,
          "PartyB": shortcode,
          "PhoneNumber": phone_number,
          "CallBackURL": lipaonline_callbackURL,
          "AccountReference": phone_number,
          "TransactionDesc": "Transfer cash"
        }

        response = requests.post(api_url, json = request, headers=headers)
        print(response.text)

