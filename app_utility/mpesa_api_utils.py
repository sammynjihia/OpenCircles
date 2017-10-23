import requests
import json
from requests.auth import HTTPBasicAuth
import datetime
import base64
from M2Crypto import RSA, X509
from base64 import b64encode

consumer_key = "iT4xDCEGuaAbQkcOVTvjm8vGl2K3jqcz"
consumer_secret = "Wwyu7nOkNGGDom6V"
api_URL = "https://api.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
main_url = "https://opencircles-mpesa-test.teamnairobi.com/"
lipaonline_callbackURL = main_url + "wallet/mpesaCallbackURL/"
shortcode = "564433"
timestamp_raw = datetime.datetime.now()
timestamp = timestamp_raw.strftime('%Y%m%d%I%M%S')
passkey = "068807038af3ff41280527fc8f6f034a17d334b997403e46798d0fb8a171a99e"
password_raw = bytes(shortcode + passkey + timestamp)
password = base64.b64encode(password_raw )

B2BResultURL = main_url + "/wallet/mpesaB2BResultURL/"
B2BQueueTimeOutURL = main_url + "/wallet/mpesaB2BQueueTimeOutURL/"
B2CResultURL = main_url + "wallet/mpesaB2CResultURL/"
B2CQueueTimeOutURL = main_url + "wallet/mpesaB2CQueueTimeoutURL/"
B2CPartyB = "254708374149"
B2CPartyA = "600232"
#B2CPartyA = "564433"
INITIATOR = "FLEMISHINFORMATICS"
INITIATOR_PASS  = "Opencircles2017!"
CERTIFICATE_FILE = "cert.cer"
security_credential2 = "ju95cBXnjD1mkvo2auzEdvRTD0k3CpfvZes9GXzkcyEXRWzpKz6e3EutzXuM/odNhmttkRv8OxmkUDNwYYKzPyQ8Irrrzej0WU9x2t9Au0seJYmzMjpa/btlqGhmpon1xQ0TzWdBQdQWB3qMHOAixZIYUGqY26YLH8gAiCAOTvAVTLE5x7zhUZuvRbWr2OZ26rpYSreIchfIUEpugmm+cazx9PKOs8dFQHS1LQWOPfyCO1Cz0rL3t/7f1AwoOOWZRNcZAgysd76HRQqrBVyrs0vqfXb6i8MHu6WQ0yWa9yzGMhyxtARtF7VJAPfQSUSusc8E1ADUvdABymviwehV7w=="





class MpesaUtils():
    def get_access_token(self):
        r = requests.get(api_URL, auth=HTTPBasicAuth(consumer_key, consumer_secret))
        mpesa_reponse = json.loads(r.text)
        access_token = mpesa_reponse['access_token']
        return access_token

    # generating security credentials
    def encryptInitiatorPassword(self):
        cert_file = open(CERTIFICATE_FILE, 'r')
        cert_data = cert_file.read()  # read certificate file
        cert_file.close()
        cert = X509.load_cert_string(cert_data)
        # pub_key = X509.load_cert_string(cert_data)
        pub_key = cert.get_pubkey()
        rsa_key = pub_key.get_rsa()
        cipher = rsa_key.public_encrypt(INITIATOR_PASS, RSA.pkcs1_padding)
        return b64encode(cipher)


    def mpesa_online_checkout(self, amount, phone_number):
        access_token = self.get_access_token()
        api_url = "https://api.safaricom.co.ke/mpesa/stkpush/v1/processrequest"
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
          "TransactionDesc": "Credit my opencircles wallet"
        }

        response = requests.post(api_url, json = request, headers=headers)
        print(response.text)
        result = response.json()
        return result

    def mpesa_b2c_checkout(self, amount, phone_number):
        access_token = self.get_access_token()
        api_url = "https://sandbox.safaricom.co.ke/mpesa/b2c/v1/paymentrequest"
        headers = {"Authorization": "Bearer %s" % access_token}
        request = {
            "InitiatorName": "testapi0232",
            "SecurityCredential": security_credential2,
            "CommandID": "SalaryPayment",
            "Amount": amount,
            "PartyA": B2CPartyA,
            "PartyB": phone_number,
            "Remarks": "Payment of business",
            "QueueTimeOutURL": B2CQueueTimeOutURL,
            "ResultURL": B2CResultURL,
            "Occasion": "sammieid30045358"
        }

        response = requests.post(api_url, json = request, headers=headers)
        result = response.json()
        return  result

    def mpesa_b2b_checkout(self, amount, account_number, paybill_number):
        access_token = self.get_access_token()
        api_url = "https://api.safaricom.co.ke/mpesa/b2b/v1/paymentrequest"
        headers = {"Authorization": "Bearer %s" % access_token}
        request = {
            "Initiator": INITIATOR,
            "SecurityCredential": self.encryptInitiatorPassword(),
            "CommandID": "BusinessPayBill",
            "SenderIdentifierType": "4",
            "RecieverIdentifierType": "4",
            "Amount": amount,
            "PartyA": shortcode,
            "PartyB": paybill_number,
            "AccountReference": account_number,
            "Remarks": "Business to business transaction ",
            "QueueTimeOutURL": B2BQueueTimeOutURL,
            "ResultURL": B2BResultURL
        }

        response = requests.post(api_url, json=request, headers=headers)

        print(response.text)
        with open('B2B_request_response_post_file.txt', 'a') as post_file:
            post_file.write(str(response.text))
            post_file.write("\n")
        result = response.json()
        return result