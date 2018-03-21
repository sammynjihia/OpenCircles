# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.conf import settings
from django.db import DatabaseError, transaction

from rest_framework.views import APIView
from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.reverse import reverse

from .serializers import *

from .models import Transactions, Wallet, B2CTransaction_log, B2BTransaction_log, MpesaTransaction_logs, \
                    AdminMpesaTransaction_logs, RevenueStreams, PendingMpesaTransactions, AirtimePurchaseLog
from member.models import Member
from circle.models import CircleMember, Circle

from shares.models import InitiativeCircleShareTransaction

from app_utility import wallet_utils, general_utils, fcm_utils, mpesa_api_utils, sms_utils, brain_tree_utils

import datetime
import json
import braintree

# Create your views here.
@api_view(['GET'])
def api_root(request,format=None):
    return Response({
             "wallet_to_wallet_tranfer":reverse("wallet-tranfer",request=request,format=format),
             "wallet_transactions":reverse("wallet-transactions",request=request,format=format),
             "mpesa_lipa_online_initiate":reverse("mpesa_lipa_online_initiate", request=request, format=format),
             "mpesa_B2C_checkout_initiate":reverse("mpesa_B2C_checkout_initiate", request=request, format=format)
    })

class WallettoWalletTranfer(APIView):
    """
    Credits and debits wallets of involved transaction parties,amount and account are to be provided
    """
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)
    def post(self, request):
        serializer = WallettoWalletTransferSerializer(data=request.data)
        created_objects = []
        if serializer.is_valid():
            sender = request.user.member
            try:
                recipient = Member.objects.get(phone_number=serializer.validated_data['phone_number'])
            except Member.DoesNotExist:
                error = "Member with the phone number does not exist"
                data = {"status":0, "message":error}
                return Response(data, status=status.HTTP_200_OK)
            circle_member_status = CircleMember.objects.filter(member=sender, is_active=False, circle__is_active=True)
            if circle_member_status.exists():
                data = {"status": 0, "message":"Unable to perform transaction."
                                               "You currently have atleast one or more deactivated circle accounts."}
                return Response(data, status=status.HTTP_200_OK)
            amount, pin = serializer.validated_data['amount'], serializer.validated_data['pin']
            account = recipient.wallet.acc_no
            if amount < 50:
                data = {"status":0, "message":"Transfers below KES 50 are not allowed"}
                return Response(data, status=status.HTTP_200_OK)
            valid, message = wallet_utils.Wallet().validate_account_info(request, amount, pin, account)
            if valid:
                general_instance = general_utils.General()
                wallet_instance = wallet_utils.Wallet()
                sender_wallet, recipient_wallet = sender.wallet, recipient.wallet
                suffix = general_instance.generate_unique_identifier('')
                sender_transaction_code = 'WTD' + suffix
                recipient_transaction_code = 'WTC' + suffix
                print("sender_wallet_balance")
                print(wallet_instance.calculate_wallet_balance(sender_wallet))
                sender_wallet_balance = wallet_instance.calculate_wallet_balance(sender_wallet) - amount
                print("sender_wallet_balance")
                print(sender_wallet_balance)
                recipient_wallet_balance = wallet_instance.calculate_wallet_balance(recipient_wallet) + amount
                sender_desc = "{} confirmed.You have sent {} {} to {} {}." \
                              "New wallet balance is {} {}.".format(sender_transaction_code,
                                                                    sender.currency,
                                                                    amount,
                                                                    recipient.user.first_name,
                                                                    recipient.user.last_name,
                                                                    sender.currency,
                                                                    sender_wallet_balance)
                recipient_desc = "{} confirmed.You have received {} {} from {} {}." \
                                 "New wallet balance is {} {}".format(recipient_transaction_code,
                                                                      recipient.currency,
                                                                      amount,
                                                                      request.user.first_name,
                                                                      request.user.last_name,
                                                                      recipient.currency,
                                                                      recipient_wallet_balance)
                try:
                    try:
                        with transaction.atomic():
                            sender_transaction = Transactions.objects.create(wallet= sender_wallet,
                                                                             transaction_type="DEBIT",
                                                                             transaction_desc=sender_desc,
                                                                             transaction_amount=amount,
                                                                             transaction_time=datetime.datetime.now(),
                                                                             recipient=account,
                                                                             transaction_code=sender_transaction_code,
                                                                             source="wallet")
                            recipient_transaction = Transactions.objects.create(wallet = recipient_wallet,
                                                                                transaction_type="CREDIT",
                                                                                transaction_desc=recipient_desc,
                                                                                transaction_amount=amount,
                                                                                transacted_by=sender_wallet.acc_no,
                                                                                transaction_time=datetime.datetime.now(),
                                                                                transaction_code=recipient_transaction_code,
                                                                                source="wallet")
                    except Exception as e:
                        print(str(e))
                        transaction.rollback()
                        data = {"status":0, "message":"Unable to process transaction"}
                        return Response(data, status=status.HTTP_200_OK)
                    instance = fcm_utils.Fcm()
                    registration_id = recipient.device_token
                    recipient_wallet_transaction = WalletTransactionsSerializer(recipient_transaction)
                    fcm_data = {"request_type":"WALLET_TO_WALLET_TRANSACTION",
                                "wallet_transaction":recipient_wallet_transaction.data}
                    sender_wallet_transaction = WalletTransactionsSerializer(sender_transaction)
                    data = {"status":1, "wallet_transaction":sender_wallet_transaction.data}
                    instance.data_push("single", registration_id, fcm_data)
                    return Response(data, status=status.HTTP_200_OK)
                except Exception as e:
                    print(str(e))
                    instance = general_utils.General()
                    instance.delete_created_objects(created_objects)
                    data = {"status":0, "message":"Unable to process transaction"}
                    return Response(data, status=status.HTTP_200_OK)
            data = { "status":0, "message":message}
            return Response(data, status=status.HTTP_200_OK)
        data = { "status":0, "message":serializer.errors}
        return Response(data, status=status.HTTP_200_OK)

class TransactionsDetails(APIView):
    """
    Fetches all transactions made by the member
    """
    authentication_classes = (TokenAuthentication,)
    permissions_classes = (IsAuthenticated,)
    def get_objects(self, request):
        wallet_transactions = Transactions.objects.filter(wallet=request.user.member.wallet)
        return wallet_transactions

    def post(self,request):
        wallet_transactions = self.get_objects(request)
        serializer = WalletTransactionsSerializer(wallet_transactions, many=True)
        data = {"status":1, "message":serializer.data}
        return Response(data, status=status.HTTP_200_OK)

class WalletTransactionDetails(APIView):
    """
    Retrieves the specific wallet transaction
    """
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)

    def post(self,request,*args,**kwargs):
        serializer = WalletTransactionSerializer(data=request.data)
        if serializer.is_valid():
            wallet_transaction = Transactions.objects.get(id=serializer.validated_data['transaction_id'])
            wallet_transaction_serializer = WalletTransactionsSerializer(wallet_transaction)
            data = {"status":1, "wallet_transaction":wallet_transaction_serializer.data}
            return Response(data, status=status.HTTP_200_OK)

class MpesaToWallet(APIView):
    """
    Credits wallet from M-pesa, amount to be provided. STKPush
    """
    authentication_classes = (TokenAuthentication,)
    permissions_class = (IsAuthenticated,)
    def post(self, request):
        serializers = MpesaToWalletSerializer(data=request.data)
        if serializers.is_valid():
            amount = serializers.validated_data["amount"]
            phone_number_raw = request.user.member.phone_number
            mpesaAPI = mpesa_api_utils.MpesaUtils()
            phone_number = phone_number_raw.strip('+')
            result = mpesaAPI.mpesa_online_checkout(amount, phone_number)

            if "errorCode" in result.keys():
                # If errorCode in response, then error has occured
                data = {"status": 0, "message": result["errorMessage"]}
                return Response(data, status=status.HTTP_200_OK)

            elif result["ResponseCode"] == '0':
                # If response from the request is ResponseCode 0 then request was accepted for processing successfully
                data = {"status": 1, "message": "Your request has been accepted successfully. "
                                                "Wait for m-pesa to process this transaction."}
                return Response(data, status=status.HTTP_200_OK)

            else:
                # If response to request as anything other than the expected then error has occured
                data = {"status": 0, "message": "Sorry! Request not sent"}
                return Response(data, status=status.HTTP_200_OK)

        data = {"status": 0, "message": serializers.errors}
        return Response(data, status=status.HTTP_200_OK)

class WalletToMpesa(APIView):
    """
    Debits wallet to M-pesa, amount, phone number and pin to be provided. B2C
    """
    authentication_classes = (TokenAuthentication,)
    permissions_class = (IsAuthenticated,)
    def post(self, request):
        serializers = WalletToMpesaSerializer(data=request.data)
        phonenumber = sms_utils.Sms()

        if serializers.is_valid():
            amount = serializers.validated_data["amount"]
            pin = serializers.validated_data["pin"]
            phone_number_raw1 = serializers.validated_data["phone_number"]
            phone_number_raw = phonenumber.format_phone_number(phone_number_raw1)
            safaricom_prefices = ['0', '1', '2', '4', '9']
            number_prefix = phone_number_raw[5]
            circle_member_status = CircleMember.objects.filter(member=request.user.member, is_active=False,
                                                               circle__is_active=True)
            if circle_member_status.exists():
                data = {"status": 0, "message": "Unable to perform transaction."
                                                "You currently have atleast one or more deactivated circle accounts."}
                return Response(data, status=status.HTTP_200_OK)

            if number_prefix in safaricom_prefices:
                mpesaAPI = mpesa_api_utils.MpesaUtils()
                phone_number = phone_number_raw.strip('+')
                validty = wallet_utils.Wallet()
                charges = 0
                if amount >= settings.MIN_MPESA and amount <= 1000:
                    charges = 16
                elif amount >= 1001 and amount <= settings.MAX_MPESA:
                    charges = 30
                else:
                    data = {"status":0, "message":"Amount must be between KES 100 and 70000"}
                    return Response(data,status=status.HTTP_200_OK)
                wallet_amount = amount + charges
                valid, message = validty.validate_account(request, pin, wallet_amount)
                if valid:
                    try:
                        result = mpesaAPI.mpesa_b2c_checkout(amount, phone_number)
                        if "errorCode" in result.keys():
                            # If errorCode in response, then request not successful, error occured
                            data = {"status":0, "message": result["errorMessage"] }
                            return Response(data, status=status.HTTP_200_OK)

                        elif result["ResponseCode"] == '0' :
                            # If ResponseCode is 0 then service request was accepted successfully
                            #log conversation id, senders phone number and recepients phone number in db
                            OriginatorConversationID = result["OriginatorConversationID"]
                            senders_PhoneNumber = request.user.member.phone_number
                            raw_recepient_PhoneNumber = phone_number
                            recepient_PhoneNumber = "+{}".format(str(raw_recepient_PhoneNumber))
                            b2c_Transaction_log = B2CTransaction_log(OriginatorConversationID=OriginatorConversationID,
                                                                     Initiator_PhoneNumber= senders_PhoneNumber,
                                                                     Recipient_PhoneNumber=recepient_PhoneNumber)
                            b2c_Transaction_log.save()

                            PendingMpesaTransactions(member=request.user.member,
                                                     originator_conversation_id=OriginatorConversationID,
                                                     amount=wallet_amount,
                                                     trx_time=datetime.datetime.now(),
                                                     is_valid=True).save()

                            print (result["ResponseDescription"])
                            data = {"status": 1, "message": "Your request has been accepted successfully. "
                                                            "Wait for m-pesa to process this transaction."}
                            return Response(data, status=status.HTTP_200_OK)
                        else:
                            #If response was unexpected then request not sent, an error occured.
                            data = {"status": 0, "message": "Sorry! Request not sent"}
                            return Response(data, status=status.HTTP_200_OK)
                    except Exception as e:
                        data = {"status":0, "message":"This transaction can not be completed at the moment."
                                                      "Kindly try again later."}
                        return Response(data, status=status.HTTP_200_OK)
                data = {"status":0, "message":message}
                return Response(data, status=status.HTTP_200_OK)
            else:
                data = {"status": 0,
                        "message": 'Sorry. We cannot complete the transaction.'
                                   ' Kindly provide a registered Safaricom phone number'}
                return Response(data, status=status.HTTP_200_OK)

        data = {"status": 0, "message": serializers.errors}
        return Response(data, status=status.HTTP_200_OK)

class MpesaCallbackURL(APIView):
    """
    callbackURL for mpesa transactions
    """
    #mpesaCallbackURL
    def post(self, request):
        data = request.body
        with open('stkpush_callbakcurl_post_file.txt', 'a') as post_file:
            post_file.write(data)
            post_file.write("\n")

        data = {"status": 1, "message": "Callback URL reached successfully by mpesa"}
        return Response(data, status=status.HTTP_200_OK)

class MpesaCallbackURL1(APIView):
    """
    callbackURL for mpesa transactions
    """
    #mpesaCallbackURL
    def post(self, request):
        data = request.body
        with open('post_file.txt', 'a') as post_file:
            post_file.write(data)
            post_file.write("\n")

        result = json.loads(data)
        print(json.dumps(result, indent=4, sort_keys=True))

        CheckoutRequestID = result["Body"]["stkCallback"]["CheckoutRequestID"]
        MerchantRequestID = result["Body"]["stkCallback"]["MerchantRequestID"]
        ResultCode = result["Body"]["stkCallback"]["ResultCode"]
        ResultDescription = result["Body"]["stkCallback"]["ResultDesc"]
        if ResultCode == '0':
            CallbackMetadata= result["Body"]["stkCallback"]["CallbackMetadata"]
            mpesa_Callbackdata = CallbackMetadata
            mpesa_data ={n['Name']:n['Value'] for n in mpesa_Callbackdata["Item"] for key,value in n.iteritems() if value in ["Amount","PhoneNumber", "MpesaReceiptNumber", "TransactionDate"]}
            transaction_code = mpesa_data["MpesaReceiptNumber"]
            amount = mpesa_data["Amount"]
            temp_phone_number =  mpesa_data["PhoneNumber"]
            phone_number = "+{}".format(str(temp_phone_number))
            transaction_date = mpesa_data["TransactionDate"]
            member = None
            created_objects = []
            try:
                try:
                    member = Member.objects.get(phone_number=phone_number)

                except Member.DoesNotExist as exp:
                    with open('member_fetched_failed.txt', 'a') as result_file:
                        result_file.write(str(exp))
                        result_file.write("\n")

                general_instance, wallet_instance = general_utils.General(),wallet_utils.Wallet()
                wallet = member.wallet
                wallet_balance =  wallet_instance.calculate_wallet_balance(wallet) + amount
                transaction_desc = "{} confirmed.You have received {} {} from {}." \
                                   "New wallet balance is {} {}.".format(transaction_code,
                                                                         member.currency,
                                                                         amount,
                                                                         phone_number,
                                                                         member.currency,
                                                                         wallet_balance)

                mpesa_transactions = Transactions(wallet=wallet, transaction_type="CREDIT",
                                                  transaction_desc=transaction_desc,
                                                  transacted_by=wallet.acc_no, transaction_amount=amount,
                                                  transaction_code=general_instance.generate_unique_identifier('WTC'))
                mpesa_transactions.save()
                with open('db_file.txt', 'a') as db_file:
                    db_file.write("Transaction {}, saved successfully ".format(transaction_code))
                    db_file.write("\n")
                created_objects.append(mpesa_transactions)
                serializer = WalletTransactionsSerializer(mpesa_transactions)
                instance = fcm_utils.Fcm()
                registration_id, title = member.device_token, "Wallet"
                message = "{} confirmed, your wallet has been credited with {} {} " \
                          "from mpesa number {} at {}".format(transaction_code,
                                                              member.currency,
                                                              amount,
                                                              phone_number,
                                                              transaction_date)
                instance.notification_push("single", registration_id, title, message)
                fcm_data = {"request_type": "MPESA_TO_WALLET_TRANSACTION",
                            "transaction": serializer.data}
                data = {"status": 1, "wallet_transaction": serializer.data}
                instance.data_push("single", registration_id, fcm_data)
                return Response(data, status=status.HTTP_200_OK)
            except Exception as e:
                instance = general_utils.General()
                instance.delete_created_objects(created_objects)
                data = {"status": 0, "message": "Unable to process transaction"}
                return Response(data, status=status.HTTP_200_OK)
        else:
            data = {"status": 0, "message": "Transaction unsuccessful, something went wrong"}
            return Response(data, status=status.HTTP_200_OK)

class MpesaB2CResultURL(APIView):
    """
    Result URL for mpesa B2C transaction
    """
    def post(self, request):
        data = request.body
        # B2C result url log file. Please do not remove.
        with open('b2c_resulturl_post_file.txt', 'a') as post_file:
            post_file.write(data)
            post_file.write("\n")
            post_file.write(str(type(data)))
            post_file.write("\n")
        result = json.loads(data)

        B2CResults = result["Result"]
        OriginatorConversationID = B2CResults["OriginatorConversationID"]
        ResultCode= int(B2CResults["ResultCode"])
        ResultDesc = B2CResults["ResultDesc"]
        TransactionID = B2CResults["TransactionID"]
        PhoneNumber = B2CTransaction_log.objects.get(OriginatorConversationID=OriginatorConversationID)
        initiatorPhoneNumber = PhoneNumber.Initiator_PhoneNumber
        mpesa_transaction = MpesaTransaction_logs(OriginatorConversationID=OriginatorConversationID,
                                                  ResultCode=ResultCode, ResultDesc=ResultDesc)
        mpesa_transaction.save()
        admin_mpesa_transaction = AdminMpesaTransaction_logs(TransactioID=TransactionID, TransactionType='B2C',
                                                             Response=data, is_committed=False)
        admin_mpesa_transaction.save()

        if ResultCode == 0:
            TransactionID = B2CResults["TransactionID"]
            ResultParameters = B2CResults["ResultParameters"]["ResultParameter"]
            mpesa_data ={n['Key']:n['Value'] for n in ResultParameters for key,value in n.iteritems() if value in
                         ["TransactionReceipt","TransactionAmount",
                          "TransactionCompletedDateTime", "ReceiverPartyPublicName"]}
            transactionAmount = mpesa_data["TransactionAmount"]
            transactionDateTime = mpesa_data["TransactionCompletedDateTime"]
            transactionReceipt = mpesa_data["TransactionReceipt"]
            receiverPartyPublicName = mpesa_data["ReceiverPartyPublicName"]
            transactionAmount = float(transactionAmount)
            charges = 0
            if transactionAmount >= settings.MIN_MPESA and transactionAmount <= 1000:
                charges = 16
                transactionAmount += charges
            else:
                charges = 30
                transactionAmount += charges
            member = None
            created_objects = []
            try:
                try:
                    member = Member.objects.get(phone_number=initiatorPhoneNumber)
                except Member.DoesNotExist as exp:
                    data = {"status":0, "message":"User does not exist."}
                    return Response(data, status=status.HTTP_200_OK)
                general_instance, wallet_instance = general_utils.General(), wallet_utils.Wallet()
                wallet = member.wallet
                wallet_balance = wallet_instance.calculate_wallet_balance(wallet) - transactionAmount
                amount_sent = transactionAmount - charges
                transaction_desc = "{} confirmed. You have sent {} {} to {} via mpesa at {}. Transaction cost {} {}." \
                                   " New wallet balance is {} {}. ".format(transactionReceipt, member.currency,
                                                                           amount_sent, receiverPartyPublicName,
                                                                           transactionDateTime, member.currency,
                                                                           charges, member.currency, wallet_balance)
                mpesa_transactions = Transactions(wallet=wallet, transaction_type="DEBIT",
                                                  transaction_desc=transaction_desc, transacted_by=wallet.acc_no,
                                                  recipient=receiverPartyPublicName,
                                                  transaction_amount=transactionAmount,
                                                  transaction_code=transactionReceipt, source="MPESA B2C")
                mpesa_transactions.save()
                admin_mpesa_transaction.is_committed=True
                admin_mpesa_transaction.save()

                pending_trx = PendingMpesaTransactions.objects.get(originator_conversation_id=OriginatorConversationID,
                                                                   member=member)
                pending_trx.is_valid = False
                pending_trx.save()


                RevenueStreams.objects.create(stream_amount=1, stream_type="SMS CHARGES",
                                              stream_code=transactionReceipt, time_of_transaction=datetime.datetime.now())
                if charges == 30:
                    RevenueStreams.objects.create(stream_amount=7, stream_type="MPESA WITHDRWAL",
                                                  stream_code=transactionReceipt,
                                                  time_of_transaction=datetime.datetime.now())

                serializer = WalletTransactionsSerializer(mpesa_transactions)
                instance = fcm_utils.Fcm()
                registration_id = member.device_token
                fcm_data = {"request_type": "WALLET_TO_MPESA_TRANSACTION",
                            "transaction": serializer.data}
                data = {"status": 1, "wallet_transaction": serializer.data}
                instance.data_push("single", registration_id, fcm_data)
                return Response(data, status=status.HTTP_200_OK)
            except Exception as e:
                instance = general_utils.General()
                instance.delete_created_objects(created_objects)
                with open('b2c_resulturl_saving_except_file.txt', 'a') as post_file:
                    post_file.write(str(e))
                    post_file.write("\n")

                data = {"status": 0, "message": "Unable to process transaction"}
                return Response(data, status=status.HTTP_200_OK)

        elif ResultCode == 2:
            admin_mpesa_transaction.is_committed = None
            admin_mpesa_transaction.save()

            pending_trx = PendingMpesaTransactions.objects.get(originator_conversation_id=OriginatorConversationID)
            pending_trx.is_valid = False
            pending_trx.save()

            instance = fcm_utils.Fcm()
            try:
                member = Member.objects.get(phone_number=initiatorPhoneNumber)
                registration_id, title = member.device_token, "Wallet to Mpesa transaction unsuccessful"
                message = " We cannot process your request at the moment. Try again later. " \
                          "If the problem persists kindly call our customer care service on +254755564433," \
                          " use M-pesa transaction code {} for reference".format(TransactionID)
                #instance.notification_push("single", registration_id, title, message)
                date_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                fcm_data = {"request_type": "SYSTEM_WARNING_MSG",
                            "title": title, "message":message, "time":date_time}
                instance.data_push("single", registration_id, fcm_data)

            except Member.DoesNotExist as exp:

                with open('member_fetched_failed.txt', 'a') as result_file:
                    result_file.write(str(exp))
                    result_file.write("\n")
            data = {"status": 0, "message": "Transaction unsuccessful, {}".format(ResultDesc)}
            return Response(data, status=status.HTTP_200_OK)

        else:
            admin_mpesa_transaction.is_committed = None
            admin_mpesa_transaction.save()

            pending_trx = PendingMpesaTransactions.objects.get(originator_conversation_id=OriginatorConversationID)
            pending_trx.is_valid = False
            pending_trx.save()

            instance = fcm_utils.Fcm()
            try:
                member = Member.objects.get(phone_number=initiatorPhoneNumber)
                registration_id, title = member.device_token, "Wallet to Mpesa transaction unsuccessful"
                message = " We cannot process your request at the moment. Try again later. " \
                          "If the problem persists kindly call our customer care service on +254755564433, " \
                          "use M-pesa transaction code {} for reference".format(TransactionID)
                #instance.notification_push("single", registration_id, title, message)
                date_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                fcm_data = {"request_type": "SYSTEM_WARNING_MSG",
                            "title": title, "message": message, "time": date_time}
                instance.data_push("single", registration_id, fcm_data)

            except Member.DoesNotExist as exp:
                with open('member_fetched_failed.txt', 'a') as result_file:
                    result_file.write(str(exp))
                    result_file.write("\n")
            data = {"status": 0, "message": "Transaction unsuccessful, something went wrong"}
            return Response(data, status=status.HTTP_200_OK)

class MpesaB2CQueueTimeoutURL(APIView):
    """
    Queue Timeout URL for mpesa B2C transaction
    """
    def post(self, request):
        data = request.body
        with open('b2c_queuetimeout_post_file.txt', 'a') as post_file:
            post_file.write(data)
            post_file.write("\n")

        result = json.loads(data)

        print ("Response from mpesa from the MpesaB2CQueueURL")
        print (result)

        return Response(status=status.HTTP_200_OK)

class MpesaC2BConfirmationURL(APIView):
    """
    URL to receive mpesa c2b comfirmation requests
    """
    def post(self, request):
        data = request.body
        # C2B result urls log file. Please Do not remove
        with open('c2b_confirmationurl_post_file.txt', 'a') as post_file:
            post_file.write(data)
            post_file.write("\n")
            post_file.write(str(type(data)))
            post_file.write("\n")
        result = json.loads(data)

        transaction_id = result["TransID"].encode()
        transaction_time = result["TransTime"].encode()
        amount = result["TransAmount"].encode()
        bill_reference = result["BillRefNumber"].encode()
        transacted_by_msisdn = result["MSISDN"].encode()
        transacted_by_firstname = result["FirstName"].encode()
        transacted_by_middlename = result["MiddleName"].encode()
        transacted_by_lastname = result["LastName"].encode()
        transacted_by = "{} {} {} {}".format(transacted_by_msisdn, transacted_by_firstname,
                                             transacted_by_middlename, transacted_by_lastname)

        admin_mpesa_transaction = AdminMpesaTransaction_logs.objects.create(TransactioID=transaction_id,
                                                                            TransactionType='C2B',
                                                                            Response=data, is_committed=False)
        # Format phone number and convert amount from string to integer
        transaction_amount = float(amount)
        phonenumber = sms_utils.Sms()
        member = None
        mpesa_transactions = None
        #Check for existence of member with that wallet account
        try:
            wallet_account = phonenumber.format_phone_number(bill_reference)
            member = Member.objects.get(phone_number=wallet_account)
        except Member.DoesNotExist:
            data = {"status": 0, "message":"Member with phone number does not exist"}
            print ("Error member does not exist")
            try:
                # check if circle exists
                circle_accNumber = bill_reference
                circle = Circle.objects.get(circle_acc_number=circle_accNumber)

            except Circle.DoesNotExist:
                data = {"status": 0, "message": "Circle with that circle account number does not exist"}
                print("Error Circle does not exist ")
                return Response(data, status=status.HTTP_200_OK)

            transaction_desc = "Initiative transaction description"
            initiative_mpesa_transactions = InitiativeCircleShareTransaction.objects.create(transaction_type="CREDIT",
                                                             transaction_desc=transaction_desc,
                                                             circle_accNumber=bill_reference,
                                                             transacted_by_msisdn=transacted_by,
                                                             num_of_shares=transaction_amount,
                                                             transaction_code=transaction_id)
            admin_mpesa_transaction.is_committed = True
            admin_mpesa_transaction.save()
            message = "{} confirmed. You have successfully deposited {} into circle {} with account {}" \
                      " on OPENCIRCLES ".format(transaction_id, transaction_amount,
                                                           circle.circle_name, circle.circle_acc_number)
            phonenumber.sendsms(transacted_by_msisdn, message)
            serializer = InitiativeSharesTransactionSerializer(initiative_mpesa_transactions)
            # instance = fcm_utils.Fcm()
            # registration_id = member.device_token # This should be the registration id of the circle admin(s)
            # fcm_data = {"request_type": "CONTRIBUTION",
            #             "transaction": serializer.data}
            # instance.data_push("single", registration_id, fcm_data)
            data = {"status": 1, "wallet_transaction": serializer.data}

            return Response(data, status=status.HTTP_200_OK)

        general_instance,wallet_instance = general_utils.General(), wallet_utils.Wallet()
        wallet = member.wallet
        wallet_balance = wallet_instance.calculate_wallet_balance(wallet) + transaction_amount
        transaction_desc = "{} confirmed.You have received {} {} from {} {} {} via mpesa. " \
                           "New wallet balance is {} {}".format(transaction_id,member.currency,
                                                                transaction_amount,
                                                                transacted_by_msisdn,
                                                                transacted_by_firstname,
                                                                transacted_by_lastname,
                                                                member.currency,
                                                                wallet_balance)
        mpesa_transactions = Transactions.objects.create(wallet=wallet, transaction_type="CREDIT",
                                                          transaction_desc=transaction_desc,
                                                          transacted_by=transacted_by, transaction_amount=transaction_amount,
                                                          transaction_code=transaction_id,
                                                          source="MPESA C2B")
        admin_mpesa_transaction.is_committed = True
        admin_mpesa_transaction.save()
        message = "{} confirmed. You have successfully credited wallet account {}" \
                  " with {} {} on OPENCIRCLES ".format(transaction_id, wallet_account,
                                                       member.currency, transaction_amount)
        phonenumber.sendsms(transacted_by_msisdn, message)
        serializer = WalletTransactionsSerializer(mpesa_transactions)
        instance = fcm_utils.Fcm()
        registration_id = member.device_token
        fcm_data = {"request_type": "MPESA_TO_WALLET_TRANSACTION",
                    "transaction": serializer.data}
        instance.data_push("single", registration_id, fcm_data)
        data = {"status": 1, "wallet_transaction": serializer.data}
        return Response(data, status=status.HTTP_200_OK)
        #If the member exists then get the member's wallet
        #Create a transaction with the given transaction details and wallet
        #Then push the notification
        # Send message to person doing the mpesa transaction confirming transaction

class MpesaC2BValidationURL(APIView):
    """
    URL to receive mpesa b2c validation requests
    """
    def post(self, request):
        data = request.body
        with open('c2b_validationurl_post_file.txt', 'a') as post_file:
            post_file.write(data)
            post_file.write("\n")

        result = json.loads(data)
        print("####################Response from mpesa from the MpesaValidationURL#############################")
        print(json.dumps(result, indent=4, sort_keys=True))

        return Response(status=status.HTTP_200_OK)

class WalletToPayBill(APIView):
    """
    Debits wallet to bank's paybill number, amount, paybill number, account number, pin and bank_name to be provided. B2B
    """
    authentication_classes = (TokenAuthentication,)
    permissions_class = (IsAuthenticated,)
    def post(self, request, *args):
        min_trx_amount = 1
        max_trx_amount = 70000
        serializers = WalletToPayBillSerializer(data=request.data)
        if serializers.is_valid():
            amount = serializers.validated_data["amount"]
            pin = serializers.validated_data["pin"]
            paybill_number = serializers.validated_data["business_number"]
            account_number = serializers.validated_data["account_number"]
            mpesaAPI = mpesa_api_utils.MpesaUtils()
            charges = 1
            wallet_amount = amount + charges
            validty, general_instance = wallet_utils.Wallet(), general_utils.General()
            has_defaulted = CircleMember.objects.filter(member=request.user.member, is_active=False)
            if has_defaulted.exists():
                data = {"status": 0,
                        "message": "Unable to transfer money.One of your accounts is currently deactivated due"
                                   " to delayed loan repayment. Kindly repay your loan."}
                return Response(data, status=status.HTTP_200_OK)
            pending_trans = PendingMpesaTransactions.objects.filter(type='B2B', purpose="paybill", is_valid=True,
                                                                    trx_time__date=datetime.date.today(),
                                                                    amount=amount, member=request.user.member)
            if pending_trans.exists():
                data = {"status": 0,
                        "message": "Unable to process request.You have a similar pending request in process."}
                return Response(data, status=status.HTTP_200_OK)
            valid, message = validty.validate_account(request, pin, wallet_amount)
            if valid:
                if amount >= min_trx_amount and amount <= max_trx_amount:
                    senders_PhoneNumber = request.user.member.phone_number
                    account_Number = account_number
                    recepient_PayBillNumber = paybill_number
                    init_paybill_unique_id = general_instance.generate_unique_identifier('FPT')
                    b2b_Transaction_log = B2BTransaction_log(OriginatorConversationID=init_paybill_unique_id,
                                                             Initiator_PhoneNumber=senders_PhoneNumber,
                                                             Recipient_PayBillNumber=recepient_PayBillNumber,
                                                             AccountNumber=account_Number).save()
                    pending_mpesa_transaction = PendingMpesaTransactions(member=request.user.member,
                                                                         originator_conversation_id=init_paybill_unique_id,
                                                                         amount=amount,
                                                                         charges=charges,
                                                                         trx_time=datetime.datetime.now(),
                                                                         is_valid=True,
                                                                         type='B2B',
                                                                         purpose='paybill').save()
                    result = mpesaAPI.mpesa_b2b_checkout(amount, account_number, paybill_number)
                    if "errorCode" in result.keys():
                        # If errorCode in response, then request not successful, error occured
                        b2b_Transaction_log.delete()
                        pending_mpesa_transaction.delete()
                        data = {"status":0, "message": result["errorMessage"] }
                        return Response(data, status=status.HTTP_200_OK)

                    elif result["ResponseCode"] == '0' :
                        # If ResponseCode is 0 then service request was accepted successfully
                        # log conversation id, senders phone number and recepients paybill number in db
                        OriginatorConversationID = result["OriginatorConversationID"]
                        b2b_Transaction_log.OriginatorConversationID=OriginatorConversationID
                        b2b_Transaction_log.save()
                        pending_mpesa_transaction.originator_conversation_id=OriginatorConversationID
                        pending_mpesa_transaction.save()
                        print(result["ResponseDescription"])
                        data = {"status": 1, "message": "Your request has been accepted successfully. "
                                                        "Wait for m-pesa to process this transaction."}
                        return Response(data, status=status.HTTP_200_OK)

                    else:
                        #If response was unexpected then request not sent, an error occured.
                        b2b_Transaction_log.delete()
                        pending_mpesa_transaction.delete()
                        data = {"status": 0, "message": "Sorry! Request not sent"}
                        return Response(data, status=status.HTTP_200_OK)

                data = {"status":0, "message": "Transaction unsuccessful, amount is not in the range of KES 1-70000"}
                return Response(data, status=status.HTTP_200_OK)
            data = {"status":0, "message":message}
            return Response(data, status=status.HTTP_200_OK)

        data = {"status": 0, "message": serializers.errors}
        return Response(data, status=status.HTTP_200_OK)

class WalletToBankPayBill(APIView):
    """
    Debits wallet to bank's paybill number, amount, paybill number, account number, pin and bank_name to be provided. B2B
    """
    authentication_classes = (TokenAuthentication,)
    permissions_class = (IsAuthenticated,)
    def post(self, request):
        min_trx_amount = 1
        max_trx_amount = 70000
        serializers = WalletToBankSerializer(data=request.data)
        if serializers.is_valid():
            amount = serializers.validated_data["amount"]
            pin = serializers.validated_data["pin"]
            paybill_number = serializers.validated_data["paybill_number"]
            account_number = serializers.validated_data["account_number"]
            bank_name = serializers.validated_data["bank_name"]
            mpesaAPI = mpesa_api_utils.MpesaUtils()
            charges = 1
            wallet_amount = amount + charges
            validty, general_instance = wallet_utils.Wallet(), general_utils.General()
            has_defaulted = CircleMember.objects.filter(member=request.user.member, is_active=False)
            if has_defaulted.exists():
                data = {"status": 0,
                        "message": "Unable to transfer money.One of your accounts is currently deactivated due"
                                   " to delayed loan repayment. Kindly repay your loan."}
                return Response(data, status=status.HTTP_200_OK)
            pending_trans = PendingMpesaTransactions.objects.filter(type='B2B', purpose="bank", is_valid=True,
                                                                    trx_time__date=datetime.date.today(),
                                                                    amount=amount, member=request.user.member)
            if pending_trans.exists():
                data = {"status": 0,
                        "message": "Unable to process request.You have a similar pending request in process."}
                return Response(data, status=status.HTTP_200_OK)
            valid, message = validty.validate_account(request, pin, wallet_amount)
            if valid:
                if amount >= min_trx_amount and amount <= max_trx_amount:
                    senders_PhoneNumber = request.user.member.phone_number
                    account_Number = account_number
                    recepient_PayBillNumber = paybill_number
                    init_bank_unique_id = general_instance.generate_unique_identifier('FBT')
                    b2b_Transaction_log = B2BTransaction_log.objects.create(OriginatorConversationID=init_bank_unique_id,
                                                             Initiator_PhoneNumber=senders_PhoneNumber,
                                                             Recipient_PayBillNumber=recepient_PayBillNumber,
                                                             AccountNumber=account_Number)
                    pending_mpesa_transaction = PendingMpesaTransactions.objects.create(member=request.user.member,
                                                                                        originator_conversation_id=init_bank_unique_id,
                                                                                        amount=amount,
                                                                                        charges=charges,
                                                                                        trx_time=datetime.datetime.now(),
                                                                                        is_valid=True,
                                                                                        type='B2B',
                                                                                        purpose='bank')
                    result = mpesaAPI.mpesa_b2b_checkout(amount, account_number, paybill_number)
                    if "errorCode" in result.keys():
                        # If errorCode in response, then request not successful, error occured
                        b2b_Transaction_log.delete()
                        pending_mpesa_transaction.delete()
                        data = {"status":0, "message": result["errorMessage"] }
                        return Response(data, status=status.HTTP_200_OK)

                    elif result["ResponseCode"] == '0' :
                        # If ResponseCode is 0 then service request was accepted successfully
                        # log conversation id, senders phone number and recepients paybill number in db
                        OriginatorConversationID = result["OriginatorConversationID"]
                        b2b_Transaction_log.OriginatorConversationID=OriginatorConversationID,
                        b2b_Transaction_log.save()
                        pending_mpesa_transaction.originator_conversation_id=OriginatorConversationID
                        pending_mpesa_transaction.save()
                        print(result["ResponseDescription"])
                        data = {"status": 1, "message": "Your request has been accepted successfully. "
                                                        "Wait for m-pesa to process this transaction."}
                        return Response(data, status=status.HTTP_200_OK)

                    else:
                        #If response was unexpected then request not sent, an error occured.
                        b2b_Transaction_log.delete()
                        pending_mpesa_transaction.delete()
                        data = {"status": 0, "message": "Sorry! Request not sent"}
                        return Response(data, status=status.HTTP_200_OK)

                data = {"status":0, "message": "Transaction unsuccessful, amount is not in the range of KES 1-70000"}
                return Response(data, status=status.HTTP_200_OK)
            data = {"status":0, "message":message}
            return Response(data, status=status.HTTP_200_OK)

        data = {"status": 0, "message": serializers.errors}
        return Response(data, status=status.HTTP_200_OK)

class MpesaB2BResultURL(APIView):
    """
    URL to receive mpesa b2b result response
    """
    def post(self, request):
        data = request.body
        with open('b2b_resulturl_post_file.txt', 'a') as post_file:
            post_file.write(data)
            post_file.write("\n")
            post_file.write(str(type(data)))
            post_file.write("\n")
        result = json.loads(data)

        B2BResults = result["Result"]
        OriginatorConversationID = B2BResults["OriginatorConversationID"]
        ResultCode = int(B2BResults["ResultCode"])
        ResultDesc = B2BResults["ResultDesc"]
        TransactionID = B2BResults["TransactionID"]

        # Save admin trx logs
        admin_mpesa_transaction = AdminMpesaTransaction_logs(TransactioID=TransactionID, TransactionType='B2B',
                                                             Response=data, is_committed=False)
        admin_mpesa_transaction.save()

        mpesa_transaction = MpesaTransaction_logs(OriginatorConversationID=OriginatorConversationID, ResultCode=ResultCode,
                                                  ResultDesc=ResultDesc)
        mpesa_transaction.save()
        b2b_trx_log = B2BTransaction_log.objects.get(OriginatorConversationID=OriginatorConversationID)
        initiatorPhoneNumber = b2b_trx_log.Initiator_PhoneNumber
        mpesa_transaction = MpesaTransaction_logs(OriginatorConversationID=OriginatorConversationID,
                                                  ResultCode=ResultCode,
                                                  ResultDesc=ResultDesc)
        mpesa_transaction.save()

        if ResultCode == 0:
            # do something
            transactionReceipt = B2BResults["TransactionID"]
            ResultParameters = B2BResults["ResultParameters"]["ResultParameter"]
            mpesa_data = {n['Key']: n['Value'] for n in ResultParameters for key, value in n.iteritems() if value in
                          ["Amount", "TransCompletedTime", "ReceiverPartyPublicName"]}
            transactionAmount = mpesa_data["Amount"]
            transactionDateTime = mpesa_data["TransCompletedTime"]
            receiverPartyPublicName = mpesa_data["ReceiverPartyPublicName"]
            BillReferenceNumber = b2b_trx_log.AccountNumber
            transactionAmount = float(transactionAmount)
            charges = 1
            created_objects = []
            try:
                member = Member.objects.get(phone_number=initiatorPhoneNumber)
                try:
                    wallet_instance = wallet_utils.Wallet()
                    wallet = member.wallet
                    try:
                        AirtimePurchaseLog.objects.get(originator_conversation_id=OriginatorConversationID,
                                                       member=member)
                        is_airtime_purchase = True
                    except AirtimePurchaseLog.DoesNotExist:
                        is_airtime_purchase = False

                    ################ africas talking purchase airtime identifier #######################
                    if is_airtime_purchase:
                        wallet_balance = wallet_instance.calculate_wallet_balance(wallet) - transactionAmount
                        transaction_desc = "{} confirmed. You bought {} {} of airtime." \
                                           "New wallet balance is {} {}.".format(transactionReceipt,
                                                                                 member.currency,
                                                                                 transactionAmount,
                                                                                 member.currency,
                                                                                 wallet_balance)

                    else:
                        transactionAmount += charges
                        wallet_balance = wallet_instance.calculate_wallet_balance(wallet) - transactionAmount
                        amount_sent = transactionAmount - charges
                        transaction_desc = "{} confirmed. {} {} has been sent to {} for account {} " \
                                           "from your wallet at {}.Transaction cost {} {}." \
                                           " New wallet balance is {} {}.".format(transactionReceipt,
                                                                                  member.currency,
                                                                                  amount_sent,
                                                                                  receiverPartyPublicName,
                                                                                  BillReferenceNumber,
                                                                                  datetime.datetime.now(),
                                                                                  member.currency,
                                                                                  charges,
                                                                                  member.currency,
                                                                                  wallet_balance)
                        RevenueStreams.objects.create(stream_amount=1, stream_type="SMS CHARGES",
                                                      stream_code=transactionReceipt,
                                                      time_of_transaction=datetime.datetime.now())
                    ####################################################################################

                    mpesa_transactions = Transactions(wallet=wallet, transaction_type="DEBIT",
                                                      transaction_desc=transaction_desc,
                                                      recipient="{} for {}".format(receiverPartyPublicName,
                                                                                   BillReferenceNumber),
                                                      transacted_by=wallet.acc_no,
                                                      transaction_amount=transactionAmount,
                                                      transaction_code=transactionReceipt, source="MPESA B2B")
                    mpesa_transactions.save()
                    admin_mpesa_transaction.is_committed = True
                    admin_mpesa_transaction.save()

                    pending_trx = PendingMpesaTransactions.objects.get(
                        originator_conversation_id=OriginatorConversationID,
                        member=member)
                    pending_trx.is_valid = False
                    pending_trx.save()
                    if is_airtime_purchase:
                        try:
                            airtime_log = AirtimePurchaseLog.objects.get(
                                originator_conversation_id=OriginatorConversationID)
                            response = sms_utils.Sms().buyairtime(airtime_log.recipient, transactionAmount)
                            is_purchased = True
                            if not response:
                                airtime_log.extra_info = "Error occured when purchasing airtime from Africastalking. " \
                                                         "Customer's wallet has been debited"
                                is_purchased = False
                            airtime_log.is_purchased = is_purchased
                            airtime_log.save()
                        except AirtimePurchaseLog.DoesNotExist:
                            with open('purchase_airtime_error_log.txt', 'a') as post_file:
                                message = "Could not fetch airtime entry of originator id {}.B2B was successful and " \
                                          "Customer's wallet has been debited".format(OriginatorConversationID)
                                post_file.write(message)
                                post_file.close()

                    serializer = WalletTransactionsSerializer(mpesa_transactions)
                    instance = fcm_utils.Fcm()
                    registration_id = member.device_token
                    fcm_data = {"request_type": "WALLET_TO_PAYBILL_TRANSACTION",
                                "transaction": serializer.data}
                    data = {"status": 1, "wallet_transaction": serializer.data}
                    instance.data_push("single", registration_id, fcm_data)
                    return Response(data, status=status.HTTP_200_OK)

                except Exception as e:
                    instance = general_utils.General()
                    instance.delete_created_objects(created_objects)
                    with open('b2b_resulturl_saving_except_file.txt', 'a') as post_file:
                        post_file.write(str(e))
                        post_file.write("\n")

                    data = {"status": 0, "message": "Unable to process transaction"}
                    return Response(data, status=status.HTTP_200_OK)

            except Member.DoesNotExist:
                with open('B2B_member_fetched_failed.txt', 'a') as result_file:
                    message = "Member with the phone number {} does not exists".format(initiatorPhoneNumber)
                    result_file.write(message)
                    result_file.write("\n")
                data = {"status": 0, "message": "Unable to process transaction"}
                return Response(data, status=status.HTTP_200_OK)

        else:
            admin_mpesa_transaction.is_committed = None
            admin_mpesa_transaction.save()

            pending_trx = PendingMpesaTransactions.objects.get(originator_conversation_id=OriginatorConversationID)
            pending_trx.is_valid = False
            pending_trx.save()
            try:
                airtime_log = AirtimePurchaseLog.objects.get(originator_conversation_id=OriginatorConversationID)
                airtime_log.extra_info = "B2B downtime. Unable to send money to Africastalking."
                airtime_log.save()
            except AirtimePurchaseLog.DoesNotExist:
                pass
            instance = fcm_utils.Fcm()
            try:
                member = Member.objects.get(phone_number=initiatorPhoneNumber)
                registration_id, title = member.device_token, "Wallet transaction unsuccessful"
                message = " We cannot process your request at the moment. Try again later." \
                          " If the problem persists kindly call our customer care service on (254) 755564433"
                date_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                fcm_data = {"request_type": "SYSTEM_WARNING_MSG", "title": title,
                            "message": message, "time": date_time}
                instance.data_push("single", registration_id, fcm_data)

            except Member.DoesNotExist:
                with open('member_fetched_failed.txt', 'a') as result_file:
                    message = "Member with the phone number {} does not exists".format(initiatorPhoneNumber)
                    result_file.write(message)
                    result_file.write("\n")

            data = {"status": 0, "message": "Transaction unsuccessful, something went wrong"}
            return Response(data, status=status.HTTP_200_OK)

class MpesaB2BQueueTimeOutURL(APIView):
    """
    URL to receive mpesa b2b queue time out response
    """
    def post(self, request):
        data = request.body
        with open('b2b_queuetimeouturl_post_file.txt', 'a') as post_file:
            post_file.write(data)
            post_file.write("\n")

        result = json.loads(data)
        print("####################Response from mpesa from the MpesaQueueTimeOutURL#############################")
        print(json.dumps(result, indent=4, sort_keys=True))

        return Response(status=status.HTTP_200_OK)

class PurchaseAirtime(APIView):
    """
    buy airtime from africastalking
    """
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)
    def post(self, request):
        serializer = PurchaseAirtimeSerializer(data=request.data)
        if serializer.is_valid():
            paybill_number = "525900"
            account_number = "sammienjihia.api"
            mpesaAPI = mpesa_api_utils.MpesaUtils()
            pin = serializer.validated_data['pin']
            amount = int(serializer.validated_data['amount'])
            if amount < 5:
                data = {"status":0, "message":"The minimum airtime one can purchase is KES 5"}
                return Response(data, status=status.HTTP_200_OK )
            wallet_instance, general_instance = wallet_utils.Wallet(), general_utils.General()
            valid, response = wallet_instance.validate_account(request, pin, amount)
            member = request.user.member
            has_defaulted = CircleMember.objects.filter(member=member, is_active=False)
            if has_defaulted.exists():
                data = {"status": 0,
                        "message": "Unable to buy airtime.One of your accounts is currently deactivated due"
                                   " to delayed loan repayment. Kindly repay your loan to be able to buy airtime."}
                return Response(data, status=status.HTTP_200_OK)
            sender_phone_number = member.phone_number
            if valid:
                pending_trans = PendingMpesaTransactions.objects.filter(type='B2B', purpose="buy airtime", is_valid=True,
                                                                        trx_time__date=datetime.date.today(),
                                                                        amount=amount, member=member)
                if pending_trans.exists():
                    data = {"status": 0,
                            "message": "Unable to process request.You have a similar pending request is in process."}
                    return Response(data, status=status.HTTP_200_OK)
                try:
                    recipient = serializer.validated_data['phone_number']
                    init_airtime_unique_id = general_instance.generate_unique_identifier('FAT')
                    airtime_log = AirtimePurchaseLog.objects.create(member=member, recipient=recipient,
                                                                    originator_conversation_id=init_airtime_unique_id,
                                                                    amount=amount)
                    b2b_transaction_log = B2BTransaction_log.objects.create(OriginatorConversationID=init_airtime_unique_id,
                                                                            Initiator_PhoneNumber=sender_phone_number,
                                                                            Recipient_PayBillNumber=paybill_number,
                                                                            AccountNumber=account_number)
                    pending_mpesa_transaction = PendingMpesaTransactions.objects.create(member=member,
                                                                                        originator_conversation_id=init_airtime_unique_id,
                                                                                        amount=amount,
                                                                                        trx_time=datetime.datetime.now(),
                                                                                        is_valid=True,
                                                                                        type='B2B',
                                                                                        purpose="buy airtime")
                    result = mpesaAPI.mpesa_b2b_checkout(amount, account_number, paybill_number)
                    if "errorCode" in result.keys():
                        # If errorCode in response, then request not successful, error occured
                        airtime_log.extra_info = "B2B returned error code"
                        airtime_log.save()
                        pending_mpesa_transaction.delete()
                        b2b_transaction_log.delete()
                        data = {"status": 0, "message": "Unable to process request.Please try Again"}
                        return Response(data, status=status.HTTP_200_OK)

                    elif result["ResponseCode"] == '0':
                        # If ResponseCode is 0 then service request was accepted successfully
                        # log conversation id, senders phone number and recepients paybill number in db
                        originator_conversation_id = result["OriginatorConversationID"]
                        airtime_log.originator_conversation_id = originator_conversation_id
                        airtime_log.save()
                        b2b_transaction_log.OriginatorConversationID = originator_conversation_id
                        b2b_transaction_log.save()
                        pending_mpesa_transaction.originator_conversation_id = originator_conversation_id
                        pending_mpesa_transaction.save()
                        print(result["ResponseDescription"])
                        data = {"status": 1, "message": "Your request has been successfully received. "
                                                        "Wait for transaction to be processed."}
                        return Response(data, status=status.HTTP_200_OK)

                    else:
                        # If response was unexpected then request not sent, an error occured.
                        airtime_log.extra_info = "B2B returned error code"
                        airtime_log.save()
                        pending_mpesa_transaction.delete()
                        b2b_transaction_log.delete()
                        data = {"status": 0, "message": "Unable to process request.Please try Again"}
                        return Response(data, status=status.HTTP_200_OK)

                except Exception as e:
                    data = {"status":0, "message":"Unable to complete request"}
                    return Response(data, status=status.HTTP_200_OK)
            data = {"status":0,"message":response}
            return Response(data, status=status.HTTP_200_OK)
        data = {"status":0, "message":serializer.errors}
        return Response(data, status=status.HTTP_200_OK)


@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def brain_tree_client_token(request):
    try:
        brain_tree_instance = brain_tree_utils.BrainTree()
        token = braintree.ClientToken.generate()
        data = {"status":1,"token":token}
    except Exception as e:
        print(str(e))
        data = {"status":0}
    return Response(data,status=status.HTTP_200_OK)

class BrainTreeTransaction(APIView):
    """
    Performs the paypal or card transaction
    """
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)

    def post(self,request):
        serializer = BrainTreeTransactionSerializer(data=request.data)
        if serializer.is_valid():
            amount, nonce = serializer.validated_data['amount'], serializer.validated_data['nonce']
            brain_tree_instance = brain_tree_utils.BrainTree()
            result = braintree.Transaction.sale({
                                                    "amount": amount,
                                                    "payment_method_nonce": nonce,
                                                    "options": {
                                                      "submit_for_settlement": True
                                                    }
                                                })
            if result.is_success:
                pass
        data = {"status":0, "message":serializer.errors}
        return Response(data, status=status.HTTP_200_OK)
