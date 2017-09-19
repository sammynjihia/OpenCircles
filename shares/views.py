from django.shortcuts import render
from django.conf import settings

from rest_framework.views import APIView
from rest_framework.decorators import api_view
from rest_framework import status
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication

from app_utility import wallet_utils

from .serializers import *
from wallet.serializers import WalletTransactionsSerializer

from wallet.models import Transactions
from shares.models import IntraCircleShareTransaction,Shares
from circle.models import Circle,CircleMember

import datetime

# Create your views here.

@api_view(['GET'])
def api_root(request,format=None):
    return Response({
                        "purchase-shares":reverse('purchase-shares',request=request,format=format),
                        "member-shares":reverse('view-shares',request=request,format=format)
    })

class PurchaseShares(APIView):
    """
    Credits shares from member wallet
    """
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)
    def post(self,request,*args,**kwargs):
        serializer = PurchaseSharesSerializer(data=request.data)
        if serializer.is_valid():
            pin,amount,circle_acc_number = serializer.validated_data['pin'],serializer.validated_data['amount'],serializer.validated_data['circle_acc_number']
            if amount < settings.MININIMUM_CIRCLE_SHARES:
                data = {"status":0,"message":"The allowed minimum purchased shares is {}".format(settings.MININIMUM_CIRCLE_SHARES)}
                return Response(data,status=status.HTTP_200_OK)
            instance = wallet_utils.Wallet()
            valid,response = instance.validate_account(request,pin,amount)
            if valid:
                try:
                    circle,member = Circle.objects.get(circle_acc_number=circle_acc_number),request.user.member
                    circle_member = CircleMember.objects.get(circle=circle,member=member)
                    wallet = member.wallet
                    desc = "Bought shares worth {}{} in circle {}".format(member.currency,amount,circle.circle_name)
                    wallet_transaction = Transactions.objects.create(wallet=wallet,transaction_type="DEBIT",transaction_time=datetime.datetime.now(),transaction_desc=desc,transaction_amount=amount,recipient=circle_acc_number)
                    shares,created = Shares.objects.get_or_create(circle_member=circle_member)
                    desc = "Purchased shares worth {} from your wallet".format(amount)
                    shares_transaction = IntraCircleShareTransaction.objects.create(shares=shares,transaction_type="DEPOSIT",sender=circle_member,recipient= circle_member,num_of_shares=amount,transaction_desc=desc)
                    shares.num_of_shares = shares.num_of_shares + amount
                    shares.save()
                    wallet_serializer = WalletTransactionsSerializer(wallet_transaction)
                    shares_serializer = SharesTransactionSerializer(shares_transaction)
                    data = {"status":1,"wallet_transaction":wallet_serializer.data,"shares_transaction":shares_serializer.data}
                    return Response(data,status=status.HTTP_200_OK)
                except Exception as e:
                    print(str(e))
                    data = {"status":0,"message":"Unable to complete transaction"}
                    return Response(data,status=status.HTTP_200_OK)
            data = {"status":0,"message":response}
            return Response(data,status=status.HTTP_200_OK)
        data = {"status":0,"message":serializer.errors}
        return Response(data,status=status.HTTP_200_OK)

class MemberShares(APIView):
    """
    Retrieves member shares
    """
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)

    def post(self,request,*args,**kwargs):
        serializer = MemberSharesSerializer(data=request.data)
        if serializer.is_valid():
            circle_acc = serializer.validated_data['circle_acc_number']
            circle = Circle.objects.get(circle_acc_number = circle_acc)
            shares = Shares.objects.get(circle_member=CircleMember.objects.get(circle=circle,member=request.user.member))
            shares_serializer = SharesSerializer(shares)
            data = {"status":1,"shares":shares_serializer.data}
            return Response(data,status=status.HTTP_200_OK)
        data = {"status":0,"message":serializer.errors}
        return Response(data,status=status.HTTP_200_OK)

class MemberSharesTransactions(APIView):
    """
    Fetches transactions for member
    """
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)

    def post(self,request,*args,**kwargs):
        serializer = MemberSharesSerializer(data=request.data)
        if serializer.is_valid():
            circle_acc = serializer.validated_data['circle_acc_number']
            circle = Circle.objects.get(circle_acc_number=circle_acc)
            circle_member = CircleMember.objects.get(member=request.user.member,circle=circle)
            shares = circle_member.shares.get()
            transactions = shares.shares_transaction.all()
            serializer = SharesTransactionSerializer(transactions,many=True,context={'request':request})
            data = {"status":1,"transactions":serializer.data}
            return Response(data,status=status.HTTP_200_OK)
        data = {"status":0,"message":serializer.errors}
        return Response(data,status=status.HTTP_200_OK)
