from django.shortcuts import render

from rest_framework.views import APIView
from rest_framework.decorators import api_view
from rest_framework import status
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication

from app_utility import wallet_utils

from .serializers import *

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
    def post(request,format,*args,**kwargs):
        serializer = PurchaseSharesSerializer(data=request.data)
        if serializer.is_valid():
            pin,amount,circle_acc_number = serializer.validated_data['pin'],float(serializer.validated_data['amount']),serializer.validated_data['circle_acc_number']
            circle,member = Circle.objects.get(circle_acc_number=circle_acc_number),request.user.member
            circlemember = CircleMember.objects.get(circle=circle,member=member)
            if request.user.check_password(pin):
                if wallet_utils.Wallet().check_balance(amount,request.user):
                    wallet,wallet_balance = member.wallet,member.wallet.balance-amount
                    desc = "Bought shares worth {}{} in circle {}".format(member.currency,amount,circle.circle_name)
                    Transactions.objects.create(wallet=wallet,transaction_type="DEBIT",transaction_time=datetime.datetime.now(),transaction_desc=desc,amount=amount,recipient=circle_acc_number)
                    wallet.update(balance=wallet_balance)
                    shares = Shares.objects.get_or_create(CircleMember=circlemember)
                    desc = "Purchased shares worth {} from your wallet".format(amount)
                    IntraCircleShareTransaction.objects.create(shares=shares,transaction_type="DEPOSIT",sender=circlemember,recipient= circlemember,num_of_shares=amount,transaction_description=desc)
                    shares.update(num_of_shares=shares.num_of_shares+amount)
                    serializer = SharesSerializer(shares)
                    data = {'status':1,'shares':serializer.data}
                    return Response(data,status=status.HTTP_200_OK)
                data = {'status':0,'message':'Insufficient funds in wallet'}
                return Response(data,status=status.HTTP_400_BAD_REQUEST)
            data = {'status':0,'message':'Invalid pin'}
            return Response(data,status=status.HTTP_400_BAD_REQUEST)
        data = {'status':0,'message':serializer.data}
        return Response(data,status=status.HTTP_400_BAD_REQUEST)

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
            serializer = SharesSerializer(shares)
            data = {'status':1,'shares':serializer.data}
            return Response(data,status=status.HTTP_200_OK)
        data = {'status':0,'message':serializer.errors}
        return Response(data,status=status.HTTP_400_BAD_REQUEST)
