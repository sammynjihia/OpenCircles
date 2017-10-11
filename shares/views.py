from django.shortcuts import render
from django.conf import settings

from rest_framework.views import APIView
from rest_framework.decorators import api_view,authentication_classes,permission_classes
from rest_framework import status
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication

from app_utility import wallet_utils,circle_utils,fcm_utils,general_utils,shares_utils

from .serializers import *
from wallet.serializers import WalletTransactionsSerializer
from shares.serializers import SharesTransactionSerializer

from wallet.models import Transactions
from shares.models import IntraCircleShareTransaction,Shares,SharesWithdrawalTariff
from circle.models import Circle,CircleMember

import datetime,uuid

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
            circle,member = Circle.objects.get(circle_acc_number=circle_acc_number),request.user.member
            if amount < settings.MININIMUM_CIRCLE_SHARES:
                data = {"status":0,"message":"The allowed minimum purchased shares is kes {}".format(settings.MININIMUM_CIRCLE_SHARES)}
                return Response(data,status=status.HTTP_200_OK)
            valid,response = shares_utils.Shares().validate_purchased_shares(amount,circle,member)
            if valid:
                instance = wallet_utils.Wallet()
                valid,response = instance.validate_account(request,pin,amount)
                if valid:
                    try:
                        circle_member = CircleMember.objects.get(circle=circle,member=member)
                        wallet = member.wallet
                        desc = "Bought shares worth {}{} in circle {}".format(member.currency,amount,circle.circle_name)
                        wallet_transaction = Transactions.objects.create(wallet=wallet,transaction_type="DEBIT",transaction_time=datetime.datetime.now(),transaction_desc=desc,transaction_amount=amount,recipient=circle_acc_number,transaction_code="WT"+uuid.uuid1().hex[:10].upper())
                        shares,created = Shares.objects.get_or_create(circle_member=circle_member)
                        desc = "Purchased shares worth {} from your wallet".format(amount)
                        shares_transaction = IntraCircleShareTransaction.objects.create(shares=shares,transaction_type="DEPOSIT",sender=circle_member,recipient= circle_member,num_of_shares=amount,transaction_desc=desc,transaction_code="ST"+uuid.uuid1().hex[:10].upper())
                        shares.num_of_shares = shares.num_of_shares + amount
                        shares.save()
                        instance = circle_utils.Circle()
                        available_shares = instance.get_available_circle_member_shares(circle,member)
                        print(available_shares)
                        fcm_available_shares = instance.get_guarantor_available_shares(circle,member)
                        wallet_serializer = WalletTransactionsSerializer(wallet_transaction)
                        shares_serializer = SharesTransactionSerializer(shares_transaction)
                        loan_limit = available_shares + settings.LOAN_LIMIT
                        data = {"status":1,"wallet_transaction":wallet_serializer.data,"shares_transaction":shares_serializer.data,"loan_limit":loan_limit}
                        instance = fcm_utils.Fcm()
                        fcm_data = {"request_type":"UPDATE_AVAILABLE_SHARES","circle_acc_number":circle.circle_acc_number,"phone_number":member.phone_number,"available_shares":fcm_available_shares}
                        registration_id = instance.get_circle_members_token(circle,member)
                        instance.data_push("multiple",registration_id,fcm_data)
                        return Response(data,status=status.HTTP_200_OK)
                    except Exception as e:
                        print(str(e))
                        data = {"status":0,"message":"Unable to complete transaction"}
                        return Response(data,status=status.HTTP_200_OK)
                data = {"status":0,"message":response}
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

class SharesWithdrawal(APIView):
    """
    Withdraw shares
    """
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)
    def post(self,request,*args,**kwargs):
        print(request.data)
        serializer = SharesWithdrawalSerializer(data=request.data)
        if serializer.is_valid():
            pin,circle = serializer.validated_data['pin'],Circle.objects.get(circle_acc_number=serializer.validated_data['circle_acc_number'])
            member = request.user.member
            created_objects = []
            if request.user.check_password(pin):
                amount = serializer.validated_data['amount']
                valid,response = shares_utils.Shares().validate_withdrawal_amount(amount)
                if valid:
                    circle_instance = circle_utils.Circle()
                    available_shares = circle_instance.get_available_circle_member_shares(circle,member)
                    print(available_shares)
                    if amount <= available_shares:
                        shares_tariff = SharesWithdrawalTariff.objects.get(max_amount__gte=amount,min_amount__lte=amount)
                        total_amount = amount + shares_tariff.amount
                        if total_amount <= available_shares:
                            try:
                                circle_member = CircleMember.objects.get(circle=circle,member=member)
                                shares = circle_member.shares.get()
                                shares.num_of_shares = shares.num_of_shares - total_amount
                                shares.save()
                                time_processed = datetime.datetime.now()
                                shares_desc = "Shares worth %s %s withdrawn.Transaction cost %s %s"%(member.currency,amount,member.currency,shares_tariff.amount)
                                shares_transaction =  IntraCircleShareTransaction.objects.create(shares=shares,transaction_type="WITHDRAW",num_of_shares=total_amount,transaction_desc=shares_desc,transaction_code="ST"+uuid.uuid1().hex[:10].upper())
                                created_objects.append(shares_transaction)
                                wallet_desc = "Credited wallet with {} {} from {} shares withdrawal".format(member.currency,amount,circle.circle_name)
                                wallet_transaction = Transactions.objects.create(wallet= member.wallet, transaction_type='CREDIT', transaction_time = time_processed,transaction_desc=wallet_desc, transaction_amount= amount,transaction_code="WT"+uuid.uuid1().hex[:10].upper())
                                created_objects.append(wallet_transaction)
                                shares_transaction_serializer = SharesTransactionSerializer(shares_transaction)
                                wallet_transaction_serializer = WalletTransactionsSerializer(wallet_transaction)
                                fcm_available_shares = circle_instance.get_guarantor_available_shares(circle,member)
                                available_shares = circle_instance.get_available_circle_member_shares(circle,member)
                                print(available_shares)
                                loan_limit = available_shares + settings.LOAN_LIMIT
                                data = {"status":1,"shares_transaction":shares_transaction_serializer.data,"wallet_transaction":wallet_transaction_serializer.data,"loan_limit":loan_limit,"message":wallet_desc}
                                instance = fcm_utils.Fcm()
                                fcm_data = {"request_type":"UPDATE_AVAILABLE_SHARES","circle_acc_number":circle.circle_acc_number,"phone_number":member.phone_number,"available_shares":fcm_available_shares}
                                registration_id = instance.get_circle_members_token(circle,member)
                                instance.data_push("multiple",registration_id,fcm_data)
                                return Response(data,status=status.HTTP_200_OK)
                            except Exception as e:
                                print(str(e))
                                general_instance = general_utils.General()
                                general_instance.delete_created_objects(created_objects)
                                data = {"status":0,"message":"Unable to process the shares withdrawal request"}
                                return Response(data,status=status.HTTP_200_OK)
                        data = {"status":0,"message":"Insufficient shares to cover the shares withdrawal charges"}
                        return Response(data,status=status.HTTP_200_OK)
                    data = {"status":0,"message":"Amount entered exceeds your available shares."}
                    return Response(data,status=status.HTTP_200_OK)
                data = {"status":0,"message":response}
                return Response(data,status=status.HTTP_200_OK)
            data = {"status":0,"message":"Invalid pin"}
            return Response(data,status=status.HTTP_200_OK)
        data = {"status":0,"message":serializer.errors}
        return Response(data,status=status.HTTP_200_OK)

@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_shares_withdrawal_tariff(request,*args,**kwargs):
    tariff = SharesWithdrawalTariff.objects.all()
    tariff_serializer = SharesTariffSerializer(tariff,many=True)
    data = {"status":1,"shares_tariff":tariff_serializer.data}
    return Response(data,status=status.HTTP_200_OK)
