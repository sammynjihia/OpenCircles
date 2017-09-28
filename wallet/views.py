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
from rest_framework.decorators import api_view
from rest_framework.reverse import reverse

from .serializers import *

from .models import Transactions,Wallet
from member.models import Member

from app_utility import wallet_utils,general_utils,fcm_utils, mpesa_api_utils

import datetime,json
import pytz

# Create your views here.
@api_view(['GET'])
def api_root(request,format=None):
    return Response({
             "wallet_to_wallet_tranfer":reverse("wallet-tranfer",request=request,format=format),
             "wallet_transactions":reverse("wallet-transactions",request=request,format=format),
             "mpesa_lipa_online_initiate":reverse("mpesa_lipa_online_initiate", request=request, format=format)
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
            try:
                recipient = Member.objects.get(phone_number=serializer.validated_data['phone_number'])
            except Member.DoesNotExist:
                error = "Member with the phone number does not exist"
                data = {"status":0,"message":error}
                return Response(data,status=status.HTTP_200_OK)
            amount,pin,account = serializer.validated_data['amount'],serializer.validated_data['pin'],recipient.wallet.acc_no
            if amount < 50:
                data = {"status":0,"message":"Transfers below kes 50 are not allowed"}
                return Response(data,status=status.HTTP_200_OK)
            valid,message = wallet_utils.Wallet().validate_account_info(request,amount,pin,account)
            if valid:
                sender_wallet,recipient_wallet = request.user.member.wallet,recipient.wallet
                sender_desc = "kes {} sent to {} {}".format(amount,recipient.user.first_name,recipient.user.last_name)
                recipient_desc = "Received kes {} from {} {}".format(amount,request.user.first_name,request.user.last_name)
                try:
                    sender_transaction = Transactions.objects.create(wallet= sender_wallet,transaction_type="DEBIT",transaction_desc=sender_desc,transaction_amount=amount,transaction_time=datetime.datetime.now(),recipient=account)
                    created_objects.append(sender_transaction)
                    recipient_transaction = Transactions.objects.create(wallet = recipient_wallet,transaction_type="CREDIT",transaction_desc=recipient_desc,transacted_by=sender_wallet.acc_no,transaction_amount=amount,transaction_time=datetime.datetime.now())
                    created_objects.append(recipient_transaction)
                    instance = fcm_utils.Fcm()
                    registration_id,title,message = recipient.device_token,"Wallet","%s %s has credited your wallet with %s %s"%(request.user.first_name,request.user.last_name,request.user.member.currency,amount)
                    instance.notification_push("single",registration_id,title,message)
                    recipient_wallet_transaction = WalletTransactionsSerializer(recipient_transaction)
                    fcm_data = {"request_type":"WALLET_TO_WALLET_TRANSACTION","transaction":recipient_wallet_transaction.data}
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
        transactions = Transactions.objects.filter(wallet=request.user.member.wallet)
        return transactions

    def post(self,request,*args,**kwargs):
        transactions = self.get_objects(request)
        serializer = WalletTransactionsSerializer(transactions,many=True)
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
            transaction = Transactions.objects.get(id=serializer.validated_data['transaction_id'])
            wallet_transaction_serializer = WalletTransactionsSerializer(transaction)
            data = {"status":1,"wallet_transaction":wallet_transaction_serializer.data}
            return Response(data,status=status.HTTP_200_OK)

class MpesaToWallet(APIView):
    """
    Credits wallet from M-pesa, amount to be provided
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
            mpesaAPI.mpesa_online_checkout(amount, phone_number)
            data = {"status": 1, "message": "Transaction Sent successfully, wait for m-pesa prompt"}
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
        # with open('post_file.txt', 'a') as post_file:
        #     post_file.write(data)
        #     post_file.write("\n")
        result = json.loads(data)
        CheckoutRequestID = result["Body"]["stkCallback"]["CheckoutRequestID"]
        MerchantRequestID = result["Body"]["stkCallback"]["MerchantRequestID"]
        ResultCode = result["Body"]["stkCallback"]["ResultCode"]

        if ResultCode == 0:
            CallbackMetadata= result["Body"]["stkCallback"]["CallbackMetadata"]
            mpesa_Callbackdata = CallbackMetadata
            mpesa_data ={n['Name']:n['Value'] for n in mpesa_Callbackdata["Item"] for key,value in n.iteritems() if value in ["Amount","PhoneNumber", "MpesaReceiptNumber", "TransactionDate"]}
            transaction_code = mpesa_data["MpesaReceiptNumber"]
            amount = mpesa_data["Amount"]
            phone_number = mpesa_data["PhoneNumber"]
            transaction_date = mpesa_data["TransactionDate"]
            m_pesa_transaction_date = datetime.datetime.fromtimestamp(transaction_date / 1e3)
            mpesa_transaction_date = pytz.timezone("Africa/Nairobi").localize(m_pesa_transaction_date, is_dst=None)
            member = Member.objects.get(phone_number=phone_number)
            with open('member_result_file.txt', 'a') as post_file:
                post_file.write(member.phone_number)
                post_file.write("\n")
            wallet = member.wallet
            transaction_desc = "{} confirmed, kes {} has been credited to your wallet by {} at {} ".format(transaction_code, amount, phone_number, mpesa_transaction_date )
            created_objects = []
            try:

                transactions = Transactions(wallet=wallet, transaction_type="CREDIT", transaction_desc=transaction_desc,
                                 transacted_by=wallet.acc_no, transaction_amount=amount,
                                 transaction_time=mpesa_transaction_date
                )
                transactions.save()
                created_objects.append(transactions)
                serializer = WalletTransactionsSerializer(transactions)
                data = {"status": 1, "wallet_transaction": serializer.data}
                print("Transaction created successfully")
                with open('stored_result_file.txt', 'a') as post_file:
                    post_file.write("stored transaction successfully")
                    post_file.write("\n")
                return Response(data, status=status.HTTP_200_OK)

            except Exception as e:
                instance = general_utils.General()
                instance.delete_created_objects(created_objects)
                data = {"status": 0, "message": "Unable to process transaction"}
                print("transaction failed to be saved to db {}".format(e))
                with open('failed_stored_result_file.txt', 'a') as post_file:
                    post_file.write("Failed to store transaction")
                    post_file.write("\n")

                return Response(data, status=status.HTTP_200_OK)
        else:
            data = {"status": 0, "message": "Transaction unsuccessful, something went wrong"}
            with open('unsuccessfultransaction_file.txt', 'a') as post_file:
                post_file.write("Transaction request sent successful, but the transaction is unsuccessful")
                post_file.write("\n")
            return Response(data, status=status.HTTP_200_OK)
