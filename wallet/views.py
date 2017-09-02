# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.shortcuts import render

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

from app_utility import wallet_utils,general_utils


import datetime

# Create your views here.
@api_view(['GET'])
def api_root(request,format=None):
    return Response({
             "wallet_to_wallet_tranfer":reverse("wallet-tranfer",request=request,format=format),
             "wallet_transactions":reverse("wallet-transactions",request=request,format=format)
    })

class WallettoWalletTranfer(APIView):
    """
    Credits and debits wallets of involved transaction parties,amount and account are to be provided
    """
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)
    def post(self,request,*args,**kwargs):
        serializer = WallettoWalletTransferSerializer(data=request.data)
        if serializer.is_valid():
            try:
                recipient = Member.objects.get(phone_number=serializer.validated_data['phone_number'])
            except Member.DoesNotExist:
                error = "Member with the phone number does not exist"
                data = {"status":0,"message":error}
                print error
                return Response(data,status=status.HTTP_400_BAD_REQUEST)
            amount,pin,account = serializer.validated_data['amount'],serializer.validated_data['pin'],recipient.wallet.acc_no
            valid,message = wallet_utils.Wallet().validate_account_info(request,amount,pin,account)
            if valid:
                sender_wallet,recipient_wallet = request.user.member.wallet,recipient.wallet
                try:
                    sender_wallet.balance = sender_wallet.balance-amount
                    recipient_wallet.balance = recipient_wallet.balance+amount
                    sender_wallet.save()
                    recipient_wallet.save()
                except Exception,e:
                    print (str(e))
                    error = "Error occurred in transaction"
                    data={"status":0,"message":error}
                    return Response(data,status=status.HTTP_400_BAD_REQUEST)
                sender_desc = "kes {} sent to {} {}".format(amount,recipient.user.first_name,recipient.user.last_name)
                recipient_desc = "Received kes {} from {} {}".format(amount,request.user.first_name,request.user.last_name)
                Transactions.objects.bulk_create([
                    Transactions(wallet= sender_wallet,transaction_type="DEBIT",transaction_desc=sender_desc,transaction_amount=amount,transaction_time=datetime.datetime.now(),recipient=account),
                    Transactions(wallet = recipient_wallet,transaction_type="CREDIT",transaction_desc=recipient_desc,transacted_by=sender_wallet.acc_no,transaction_amount=amount,transaction_time=datetime.datetime.now())
                ])
                data = {"status":1}
                return Response(data,status=status.HTTP_200_OK)
            data = { "status":0,"message":message}
            print message
            return Response(data,status=status.HTTP_200_OK)

        data = { "status":0,"message":serializer.errors}
        print serializer.errors
        return Response(data,status=status.HTTP_200_OK)


class TransactionDetails(APIView):
    """
    Fetches all transactions made by the member
    """
    authentication_classes = (TokenAuthentication,)
    permissions_class = (IsAuthenticated,)
    def get_objects(self,request):
        transactions = Transactions.objects.filter(wallet=request.user.member.wallet)
        return transactions

    def post(self,request,*args,**kwargs):
        transactions = self.get_objects(request)
        serializer = WalletTransactionsSerializer(transactions,many=True)
        data = {"status":1,"message":serializer.data}
        return Response(data,status=status.HTTP_200_OK)
