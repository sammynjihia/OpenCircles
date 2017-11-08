# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.utils.dateparse import parse_datetime
from django.shortcuts import render

from wallet import disable_csrf
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from rest_framework.decorators import api_view,authentication_classes,permission_classes
from rest_framework.reverse import reverse

from .serializers import *

from .models import Transactions,Wallet, B2CTransaction_log, B2BTransaction_log, MpesaTransaction_logs, AdminMpesaTransaction_logs
from member.models import Member
from django.core.exceptions import ValidationError

from django.db import DatabaseError,transaction

from app_utility import wallet_utils,general_utils,fcm_utils, mpesa_api_utils, sms_utils, brain_tree_utils

import datetime,json
import pytz,uuid
import math
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
    def post(self,request,*args,**kwargs):
        serializer = WallettoWalletTransferSerializer(data=request.data)
        created_objects = []
        if serializer.is_valid():
            sender = request.user.member
            try:
                recipient = Member.objects.get(phone_number=serializer.validated_data['phone_number'])
            except Member.DoesNotExist:
                error = "Member with the phone number does not exist"
                data = {"status":0,"message":error}
                return Response(data,status=status.HTTP_200_OK)
            amount,pin,account = serializer.validated_data['amount'],serializer.validated_data['pin'],recipient.wallet.acc_no
            if amount < 50:
                data = {"status":0,"message":"Transfers below KES 50 are not allowed"}
                return Response(data,status=status.HTTP_200_OK)
            valid,message = wallet_utils.Wallet().validate_account_info(request,amount,pin,account)
            if valid:
                general_instance = general_utils.General()
                wallet_instance = wallet_utils.Wallet()
                sender_wallet,recipient_wallet = sender.wallet,recipient.wallet
                suffix = general_instance.generate_unique_identifier('')
                sender_transaction_code = 'WTD' + suffix
                recipient_transaction_code = 'WTC' + suffix
                print("sender_wallet_balance")
                print(wallet_instance.calculate_wallet_balance(sender_wallet))
                sender_wallet_balance = wallet_instance.calculate_wallet_balance(sender_wallet) - amount
                print("sender_wallet_balance")
                print(sender_wallet_balance)
                recipient_wallet_balance = wallet_instance.calculate_wallet_balance(recipient_wallet) + amount
                sender_desc = "{} confirmed.You have sent {} {} to {} {}.New wallet balance is {} {}.".format(sender_transaction_code, sender.currency, amount, recipient.user.first_name, recipient.user.last_name, sender.currency, sender_wallet_balance)
                recipient_desc = "{} confirmed.You have received {} {} from {} {}.New wallet balance is {} {}".format(recipient_transaction_code, recipient.currency, amount, request.user.first_name, request.user.last_name, recipient.currency, recipient_wallet_balance)
                try:
                    try:
                        with transaction.atomic():
                            sender_transaction = Transactions.objects.create(wallet= sender_wallet, transaction_type="DEBIT", transaction_desc=sender_desc, transaction_amount=amount, transaction_time=datetime.datetime.now(), recipient=account, transaction_code=sender_transaction_code, source="wallet")
                            recipient_transaction = Transactions.objects.create(wallet = recipient_wallet, transaction_type="CREDIT", transaction_desc=recipient_desc, transaction_amount=amount,transacted_by=sender_wallet.acc_no, transaction_time=datetime.datetime.now(), transaction_code=recipient_transaction_code, source="wallet")
                    except Exception as e:
                        print(str(e))
                        transaction.rollback()
                        data = {"status":0,"message":"Unable to process transaction"}
                        return Response(data,status=status.HTTP_200_OK)
                    instance = fcm_utils.Fcm()
                    registration_id,title,message = recipient.device_token,"Wallet","%s %s has credited your wallet with %s %s"%(request.user.first_name,request.user.last_name,request.user.member.currency,amount)
                    instance.notification_push("single",registration_id,title,message)
                    recipient_wallet_transaction = WalletTransactionsSerializer(recipient_transaction)
                    fcm_data = {"request_type":"WALLET_TO_WALLET_TRANSACTION","wallet_transaction":recipient_wallet_transaction.data}
                    sender_wallet_transaction = WalletTransactionsSerializer(sender_transaction)
                    data = {"status":1,"wallet_transaction":sender_wallet_transaction.data}
                    instance.data_push("single",registration_id,fcm_data)
                    return Response(data,status=status.HTTP_200_OK)
                except Exception as e:
                    print(str(e))
                    instance = general_utils.General()
                    instance.delete_created_objects(created_objects)
                    data = {"status":0,"message":"Unable to process transaction"}
                    return Response(data,status=status.HTTP_200_OK)
            data = { "status":0,"message":message}
            return Response(data,status=status.HTTP_200_OK)
        data = { "status":0,"message":serializer.errors}
        return Response(data,status=status.HTTP_200_OK)

class TransactionsDetails(APIView):
    """
    Fetches all transactions made by the member
    """
    authentication_classes = (TokenAuthentication,)
    permissions_classes = (IsAuthenticated,)
    def get_objects(self,request):
        wallet_transactions = Transactions.objects.filter(wallet=request.user.member.wallet)
        return wallet_transactions

    def post(self,request,*args,**kwargs):
        wallet_transactions = self.get_objects(request)
        serializer = WalletTransactionsSerializer(wallet_transactions,many=True)
        data = {"status":1,"message":serializer.data}
        return Response(data,status=status.HTTP_200_OK)

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
            data = {"status":1,"wallet_transaction":wallet_transaction_serializer.data}
            return Response(data,status=status.HTTP_200_OK)

class MpesaToWallet(APIView):
    """
    Credits wallet from M-pesa, amount to be provided. STKPush
    """
    authentication_classes = (TokenAuthentication,)
    permissions_class = (IsAuthenticated,)
    def post(self, request, *args):
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
                data = {"status": 1, "message": "{}. Wait for mpesa prompt".format(result["ResponseDescription"])}
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
    def post(self, request, *args):
        serializers = WalletToMpesaSerializer(data=request.data)
        phonenumber = sms_utils.Sms()
        if serializers.is_valid():
            amount = serializers.validated_data["amount"]
            pin = serializers.validated_data["pin"]
            phone_number_raw1 = serializers.validated_data["phone_number"]
            phone_number_raw = phonenumber.format_phone_number(phone_number_raw1)
            mpesaAPI = mpesa_api_utils.MpesaUtils()
            phone_number = phone_number_raw.strip('+')

            validty = wallet_utils.Wallet()
            valid, message = validty.validate_account(request, pin, amount)
            if valid:
                if 200 <= amount <=70000:
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
                        b2c_Transaction_log = B2CTransaction_log(OriginatorConversationID=OriginatorConversationID, Initiator_PhoneNumber= senders_PhoneNumber,
                                                                 Recipient_PhoneNumber=recepient_PhoneNumber)
                        b2c_Transaction_log.save()
                        print (result["ResponseDescription"])
                        data = {"status": 1, "message": result["ResponseDescription"]}
                        return Response(data, status=status.HTTP_200_OK)

                    else:
                        #If response was unexpected then request not sent, an error occured.
                        data = {"status": 0, "message": "Sorry! Request not sent"}
                        return Response(data, status=status.HTTP_200_OK)

                data = {"status":0, "message": "Transaction unsuccessful, amount is not in the range of 200-70000"}
                return Response(data, status=status.HTTP_200_OK)
            data = {"status":0, "message":message}
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
                transaction_desc = "{} confirmed.You have received {} {} from {}.New wallet balance is {} {}." \
                    .format(transaction_code, member.currency, amount, phone_number, member.currency, wallet_balance)

                mpesa_transactions = Transactions(wallet=wallet, transaction_type="CREDIT",
                                                  transaction_desc=transaction_desc,
                                                  transacted_by=wallet.acc_no, transaction_amount=amount,transaction_code=general_instance.generate_unique_identifier('WTC'))
                mpesa_transactions.save()
                with open('db_file.txt', 'a') as db_file:
                    db_file.write("Transaction {}, saved successfully ".format(transaction_code))
                    db_file.write("\n")
                created_objects.append(mpesa_transactions)
                serializer = WalletTransactionsSerializer(mpesa_transactions)
                instance = fcm_utils.Fcm()
                registration_id, title, message = member.device_token, "Wallet", "{} confirmed, your wallet has been credited with {} {} from mpesa" \
                                                                                 " number {} at {}".format(
                    transaction_code, member.currency, amount, phone_number, transaction_date)
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
        with open('b2c_resulturl_post_file.txt', 'a') as post_file:
            post_file.write(data)
            post_file.write("\n")
            post_file.write(str(type(data)))
            post_file.write("\n")
        result = json.loads(data)
        with open('b2c_resulting.txt', 'a') as result_file:
            result_file.write(str(result))
            result_file.write("\n")
        print (json.dumps(result, indent=4, sort_keys=True))

        B2CResults = result["Result"]
        OriginatorConversationID = B2CResults["OriginatorConversationID"]
        ResultCode= B2CResults["ResultCode"]
        ResultDesc = B2CResults["ResultDesc"]
        TransactionID = B2CResults["TransactionID"]
        PhoneNumber = B2CTransaction_log.objects.get(OriginatorConversationID=OriginatorConversationID)
        initiatorPhoneNumber = PhoneNumber.Initiator_PhoneNumber

        try:
            mpesa_transaction = MpesaTransaction_logs(OriginatorConversationID=OriginatorConversationID, ResultCode=ResultCode,
                                                      ResultDesc=ResultDesc)
            mpesa_transaction.save()
            admin_mpesa_transaction = AdminMpesaTransaction_logs(TransactioID=TransactionID, TransactionType='B2C', Response=data)
            admin_mpesa_transaction.save()
        except ValidationError as e:
            data = {"status": 0, "message": "Database transaction unsuccessful, object already exist"}
            return Response(data, status=status.HTTP_200_OK)


        if ResultCode == '0':
            TransactionID = B2CResults["TransactionID"]
            ResultParameters = B2CResults["ResultParameters"]["ResultParameter"]
            mpesa_data ={n['Key']:n['Value'] for n in ResultParameters for key,value in n.iteritems() if value in
                         ["TransactionReceipt","TransactionAmount", "TransactionCompletedDateTime", "ReceiverPartyPublicName"]}
            transactionAmount = mpesa_data["TransactionAmount"]
            transactionDateTime = mpesa_data["TransactionCompletedDateTime"]
            transactionReceipt = mpesa_data["TransactionReceipt"]
            receiverPartyPublicName = mpesa_data["ReceiverPartyPublicName"]
            transactionAmount = float(transactionAmount)

            member = None
            created_objects = []
            try:
                try:
                    member = Member.objects.get(phone_number=initiatorPhoneNumber)

                except Member.DoesNotExist as exp:
                    print("*"*90)
                    print(initiatorPhoneNumber)
                    with open('member_fetched_failed.txt', 'a') as result_file:
                        result_file.write(str(exp))
                        result_file.write("\n")
                general_instance, wallet_instance = general_utils.General(), wallet_utils.Wallet()
                wallet = member.wallet
                wallet_balance = wallet_instance.calculate_wallet_balance(wallet) - transactionAmount
                transaction_desc = "{} confirmed.{} {} has been sent to {} from your wallet at {}.New wallet balance is {} {}. " \
                    .format(transactionReceipt, member.currency, transactionAmount, receiverPartyPublicName, transactionDateTime, member.currency, wallet_balance)
                mpesa_transactions = Transactions(wallet=wallet, transaction_type="DEBIT",
                                                  transaction_desc=transaction_desc,
                                                  transacted_by=wallet.acc_no, transaction_amount=transactionAmount,transation_code=general_instance.generate_unique_identifier('WTD'))
                mpesa_transactions.save()
                with open('db_file.txt', 'a') as db_file:
                    db_file.write("Transaction {}, saved successfully ".format(transactionReceipt))
                    db_file.write("\n")
                created_objects.append(mpesa_transactions)
                serializer = WalletTransactionsSerializer(mpesa_transactions)
                instance = fcm_utils.Fcm()
                registration_id, title, message = member.device_token, "Wallet", "{} confirmed, {} {} has been debited from your wallet to {} at {} " \
                    .format(transactionReceipt, member.currency, transactionAmount, receiverPartyPublicName, transactionDateTime)
                fcm_data = {"request_type": "WALLET_TO_MPESA_TRANSACTION",
                            "transaction": serializer.data}
                data = {"status": 1, "wallet_transaction": serializer.data}
                instance.data_push("single", registration_id, fcm_data)
                return Response(data, status=status.HTTP_200_OK)
            except Exception as e:
                instance = general_utils.General()
                instance.delete_created_objects(created_objects)
                data = {"status": 0, "message": "Unable to process transaction"}
                return Response(data, status=status.HTTP_200_OK)

        elif ResultCode == '2' :
            instance = fcm_utils.Fcm()
            try:
                member = Member.objects.get(phone_number=initiatorPhoneNumber)
                registration_id, title, message = member.device_token, "Wallet to Mpesa transaction unsuccessful", " We cannot process your request at the moment. Try again later. If the problem persists" \
                                                                                 " kindly call our customer care service on (254) 795891656, use M-pesa transaction code {} for reference".format(TransactionID)
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
            instance = fcm_utils.Fcm()
            try:
                member = Member.objects.get(phone_number=initiatorPhoneNumber)
                registration_id, title, message = member.device_token, "Wallet to Mpesa transaction unsuccessful", " We cannot process your request at the moment. Try again later. If the problem persists" \
                                                                                 " kindly call our customer care service on (254) 795891656, use M-pesa transaction code {} for reference".format(TransactionID)
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
        with open('c2b_confirmationurl_post_file.txt', 'a') as post_file:
            post_file.write(data)
            post_file.write("\n")
            post_file.write(str(type(data)))
            post_file.write("\n")

        result = json.loads(data)

        transaction_id = result["TransID"].encode()
        transaction_time = result["TransTime"].encode()
        amount = result["TransAmount"].encode()
        phone_number = result["BillRefNumber"].encode()
        transacted_by_msisdn = result["MSISDN"].encode()
        transacted_by_firstname = result["FirstName"].encode()
        transacted_by_lastname = result["LastName"].encode()

        try:
            admin_mpesa_transaction = AdminMpesaTransaction_logs(TransactioID=transaction_id, TransactionType='C2B', Response=data)
            admin_mpesa_transaction.save()
        except Exception as e:
            data = {"status": 0, "message": "Database transaction unsuccessful, object already exist"}
            return Response(data, status=status.HTTP_200_OK)

        # Format phone number and convert amount from string to integer
        transaction_amount = float(amount)
        phonenumber = sms_utils.Sms()
        wallet_account = phonenumber.format_phone_number(phone_number)

        member = None
        mpesa_transactions = None

        #Check for existence of member with that wallet account
        try:
            try:
                member = Member.objects.get(phone_number=wallet_account)
            except Member.DoesNotExist as exp:
                with open('c2b_member_fetched_failed.txt', 'a') as result_file:
                    result_file.write(str(exp))
                    result_file.write("\n")

            general_instance,wallet_instance = general_utils.General(), wallet_utils.Wallet()
            unique_identifier = general_instance.generate_unique_identifier('WTC')
            wallet = member.wallet
            wallet_balance = wallet_instance.calculate_wallet_balance(wallet) + transaction_amount
            transaction_desc = "{} confirmed.{} {} has been credited to your wallet by {} {} {}.New wallet balance is {} {}".format(unique_identifier,member.currency, transaction_amount, transacted_by_msisdn, transacted_by_firstname, transacted_by_lastname, member.currency, wallet_balance)
            try:
                mpesa_transactions = Transactions.objects.create(wallet=wallet, transaction_type="CREDIT",
                                                  transaction_desc=transaction_desc,
                                                  transacted_by=wallet.acc_no, transaction_amount=transaction_amount,
                                                  transaction_code=unique_identifier)
            except Exception as e:
                with open('c2b_transaction_creation_failed.txt', 'a') as result_file:
                    result_file.write(str(e))
                    result_file.write("\n")
            message = "{} confirmed. You have successfully credited wallet account {} with {} {} on OPENCIRCLES ".format(unique_identifier, wallet_account,
                                         member.currency, transaction_amount)

            phonenumber.sendsms(transacted_by_msisdn, message)
            serializer = WalletTransactionsSerializer(mpesa_transactions)
            instance = fcm_utils.Fcm()
            registration_id, title, message = member.device_token, "Wallet", "{} confirmed, your wallet has been credited with {} {} from mpesa" \
                                                                             " number {} at {}".format(
                unique_identifier, member.currency, transaction_amount, transacted_by_msisdn, transaction_time)
            instance.notification_push("single", registration_id, title, message)
            fcm_data = {"request_type": "MPESA_TO_WALLET_TRANSACTION",
                        "transaction": serializer.data}
            data = {"status": 1, "wallet_transaction": serializer.data}
            instance.data_push("single", registration_id, fcm_data)
            return Response(data, status=status.HTTP_200_OK)

        except Exception as exp:
            with open('c2b_failure_exception.txt', 'a') as result_file:
                result_file.write(str(exp))
                result_file.write("\n")

        data = {"status": 0, "message": "Unable to process transaction"}
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
    Debits wallet to business paybill, amount, paybill number, account number and pin to be provided. B2B
    """
    authentication_classes = (TokenAuthentication,)
    permissions_class = (IsAuthenticated,)
    def post(self, request, *args):
        serializers = WalletToPayBillSerializer(data=request.data)
        if serializers.is_valid():
            raw_amount = serializers.validated_data["amount"]
            pin = serializers.validated_data["pin"]
            paybill_number = serializers.validated_data["business_number"]
            account_number = serializers.validated_data["account_number"]
            mpesaAPI = mpesa_api_utils.MpesaUtils()
            charges = (5/100)*raw_amount
            amount = raw_amount + math.ceil(charges)
            amount = int(amount)

            validty = wallet_utils.Wallet()
            valid, message = validty.validate_account(request, pin, amount)
            if valid:
                if 200 <= amount <=70000:
                    result = mpesaAPI.mpesa_b2b_checkout(amount, account_number, paybill_number)

                    if "errorCode" in result.keys():
                        # If errorCode in response, then request not successful, error occured
                        data = {"status":0, "message": result["errorMessage"] }
                        return Response(data, status=status.HTTP_200_OK)

                    elif result["ResponseCode"] == '0' :
                        # If ResponseCode is 0 then service request was accepted successfully
                        # If ResponseCode is 0 then service request was accepted successfully
                        # log conversation id, senders phone number and recepients paybill number in db
                        OriginatorConversationID = result["OriginatorConversationID"]
                        senders_PhoneNumber = request.user.member.phone_number
                        account_Number = account_number
                        recepient_PayBillNumber = paybill_number
                        b2b_Transaction_log = B2BTransaction_log(OriginatorConversationID=OriginatorConversationID,
                                                                 Initiator_PhoneNumber=senders_PhoneNumber,
                                                                 Recipient_PayBillNumber=recepient_PayBillNumber,
                                                                 AccountNumber=account_Number)
                        b2b_Transaction_log.save()
                        print(result["ResponseDescription"])
                        data = {"status": 1, "message": result["ResponseDescription"]}
                        return Response(data, status=status.HTTP_200_OK)

                    else:
                        #If response was unexpected then request not sent, an error occured.
                        data = {"status": 0, "message": "Sorry! Request not sent"}
                        return Response(data, status=status.HTTP_200_OK)

                data = {"status":0, "message": "Transaction unsuccessful, amount is not in the range of 200-70000"}
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
        print("####################Response from mpesa from the MpesaB2BResultURL#############################")
        print(json.dumps(result, indent=4, sort_keys=True))

        B2BResults = result["Result"]
        OriginatorConversationID = B2BResults["OriginatorConversationID"]
        ResultCode = B2BResults["ResultCode"]
        ResultDesc = B2BResults["ResultDesc"]
        TransactionID = B2BResults["TransactionID"]
        PhoneNumber = B2BTransaction_log.objects.get(OriginatorConversationID=OriginatorConversationID)
        initiatorPhoneNumber = PhoneNumber.Initiator_PhoneNumber

        try:
            mpesa_transaction = MpesaTransaction_logs(OriginatorConversationID=OriginatorConversationID, ResultCode=ResultCode,
                                                      ResultDesc=ResultDesc)
            mpesa_transaction.save()
            admin_mpesa_transaction = AdminMpesaTransaction_logs(TransactioID=TransactionID, TransactionType='B2B',
                                                                 Response=data)
            admin_mpesa_transaction.save()
            with open('b2b_result_try_post_file.txt', 'a') as post_file:
                post_file.write(data)
                post_file.write("\n")
        except ValidationError as e:
            data = {"status": 0, "message": "Database transaction unsuccessful, object already exist"}
            return Response(data, status=status.HTTP_200_OK)

        if ResultCode == '0':
            # do something
            TransactionID = B2BResults["TransactionID"]
            ResultParameters = B2BResults["ResultParameters"]["ResultParameter"]
            mpesa_data = {n['Key']: n['Value'] for n in ResultParameters for key, value in n.iteritems() if value in
                          ["Amount", "TransCompletedTime", "ReceiverPartyPublicName"]}
            transactionAmount = mpesa_data["Amount"]
            transactionDateTime = mpesa_data["TransCompletedTime"]
            transactionReceipt = TransactionID
            receiverPartyPublicName = mpesa_data["ReceiverPartyPublicName"]
            BillReferenceNumber = PhoneNumber.AccountNumber
            transactionAmount = float(transactionAmount)

            member = None
            created_objects = []

            try:

                try:
                    member=Member.objects.get(phone_number=initiatorPhoneNumber)
                except Member.DoesNotExist as exp:
                    with open('B2B_member_fetched_failed.txt', 'a') as result_file:
                        result_file.write(str(exp))
                        result_file.write("\n")

                    general_instance, wallet_instance = general_utils.General(), wallet_utils.Wallet()
                    wallet = member.wallet
                    wallet_balance =  wallet_instance.calculate_wallet_balance(wallet) - transactionAmount
                    transaction_desc = "{} confirmed.{} {} has been sent to {} for account {} from your wallet at {}.New wallet balance is {} {}." \
                        .format(transactionReceipt, member.currency, transactionAmount, receiverPartyPublicName, BillReferenceNumber, transactionDateTime, member.currency, wallet_balance)

                    mpesa_transactions = Transactions(wallet=wallet, transaction_type="DEBIT",
                                                      transaction_desc=transaction_desc,
                                                      transacted_by=wallet.acc_no, transaction_amount=transactionAmount,
                                                      transation_code=general_instance.generate_unique_identifier(
                                                          'WTD'))
                    mpesa_transactions.save()
                    with open('b2b_db_file.txt', 'a') as db_file:
                        db_file.write("Transaction {}, saved successfully ".format(transactionReceipt))
                        db_file.write("\n")
                    created_objects.append(mpesa_transactions)
                    serializer = WalletTransactionsSerializer(mpesa_transactions)
                    instance = fcm_utils.Fcm()
                    registration_id, title, message = member.device_token, "Wallet", "{} confirmed, {} {} has been debited from your wallet to {} at {} " \
                        .format(transactionReceipt, member.currency, transactionAmount, receiverPartyPublicName, transactionDateTime)

                    #instance.notification_push("single", registration_id, title, message)
                    fcm_data = {"request_type": "WALLET_TO_PAYBILL_TRANSACTION",
                                "transaction": serializer.data}
                    data = {"status": 1, "wallet_transaction": serializer.data}
                    instance.data_push("single", registration_id, fcm_data)
                    return Response(data, status=status.HTTP_200_OK)
            except Exception as e:
                print (str(e))
        else:
            instance = fcm_utils.Fcm()
            try:
                member = Member.objects.get(phone_number=initiatorPhoneNumber)
                registration_id, title, message = member.device_token, "Wallet to Paybill transaction unsuccessful", " We cannot process your request at the moment. Try again later. If the problem persists" \
                                                                                                                   " kindly call our customer care service on (254) 795891656, use M-pesa transaction code {} for reference".format(TransactionID)
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

        return Response(status=status.HTTP_200_OK)


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
