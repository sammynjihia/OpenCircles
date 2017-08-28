# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.shortcuts import render

from rest_framework.views import APIView
from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view
from rest_framework.reverse import reverse

from .serializers import *
from .models import Transactions,Wallet

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
    permission_classes = (IsAuthenticated,)
    def post(self,request,*args,**kwargs):
        keys = ["amount","account"]
        del_ses = general_utils.General()
        if 'amount' in request.session:
            serializer = WalletTranferConfirmationSerializer(data=request.data)
        else:
            serializer = WallettoWalletTransferSerializer(data=request.data)
            if serializer.is_valid():
                keys.append("pin")
                wallet = wallet_utils.Wallet()
                for key in keys:
                    request.session[key] = serializer.validated_data[key]
                valid,message = wallet.validate_account_info(request)
                if valid:
                    recipient = Wallet.objects.get(acc_no=request.session["account"]).member.user
                    full_name = "%s %s"%(recipient.first_name,recipient.last_name)
                    keys.remove("pin")
                    del request.session["pin"]
                    data = {"status":1,"full_name":full_name,"amount":request.session["amount"]}
                    return Response(data,status=status.HTTP_200_OK)
                del_ses.delete_sessions(request,keys)
                data = {"status":0,"message":message}
                return Response(data,status=status.HTTP_400_BAD_REQUEST)
            data = { "status":0,"message":serializer.errors}
            return Response(data,status=status.HTTP_400_BAD_REQUEST)
        if serializer.is_valid():
            if serializer.validated_data['confirmed'] == "yes":
                amount,account = request.session["amount"],request.session["account"]
                sender_wallet,recipient_wallet = request.user.member.wallet,Wallet.objects.get(acc_no=account)
                try:
                    sender_wallet.balance = sender_wallet.balance - amount
                    recipient_wallet.balance = recipient_wallet.balance + amount
                    sender_wallet.save()
                    recipient_wallet.save()
                except Exception,e:
                    print (str(e))
                    del_ses.delete_sessions(request,keys)
                    data={"status":0,"message":"Error occurred in transaction"}
                    return Response(data,status=status.HTTP_400_BAD_REQUEST)

                Transactions.objects.bulk_create([
                    Transactions(wallet= sender_wallet,transaction_type="DEBIT",transaction_desc="wallet to wallet transfer",transaction_amount=amount,transaction_time=datetime.datetime.now(),recipient=account),
                    Transactions(wallet = recipient_wallet,transaction_type="CREDIT",transaction_desc="wallet to wallet transfer",transacted_by=sender_wallet.acc_no,transaction_amount=amount,transaction_time=datetime.datetime.now())
                ])
                del_ses.delete_sessions(request,keys)
                data = {"status":1,"message":"Transaction completed"}
                return Response(data,status=status.HTTP_200_OK)

        del_ses.delete_sessions(request,keys)
        data = { "status":0,"message":serializer.errors}
        return Response(data,status=status.HTTP_400_BAD_REQUEST)


class TransactionDetails(APIView):
    """
    Fetches all transactions made by the member
    """
    permissions_class = (IsAuthenticated,)
    def get_objects(self,request):
        transactions = Transactions.objects.filter(wallet=request.user.member.wallet)
        return transactions

    def get(self,request,*args,**kwargs):
        transactions = self.get_objects(request)
        serializer = WalletTransactionsSerializer(transactions,many=True)
        data = {"status":1,"message":serializer.data}
        return Response(data,status=status.HTTP_200_OK)
