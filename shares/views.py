from django.shortcuts import render
from django.conf import settings

from rest_framework.views import APIView
from rest_framework.decorators import api_view,authentication_classes,permission_classes
from rest_framework import status
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication

from app_utility import wallet_utils,circle_utils,fcm_utils,general_utils,shares_utils,loan_utils

from .serializers import *
from wallet.serializers import WalletTransactionsSerializer
from shares.serializers import SharesTransactionSerializer

from wallet.models import Transactions,RevenueStreams
from shares.models import IntraCircleShareTransaction,Shares,SharesWithdrawalTariff
from circle.models import Circle,CircleMember

from loan.tasks import unlocking_guarantors_shares, updating_loan_limit, sending_guarantee_requests, task_share_loan_interest

import datetime,uuid

# Create your views here.

@api_view(['GET'])
def api_root(request, format=None):
    return Response({
                        "purchase-shares":reverse('purchase-shares', request=request, format=format),
                        "member-shares":reverse('view-shares', request=request, format=format)
    })

class PurchaseShares(APIView):
    """
    Credits shares from member wallet
    """
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)
    def post(self, request, *args, **kwargs):
        serializer = PurchaseSharesSerializer(data=request.data)
        if serializer.is_valid():
            pin, amount, circle_acc_number = serializer.validated_data['pin'], serializer.validated_data['amount'], serializer.validated_data['circle_acc_number']
            circle, member = Circle.objects.get(circle_acc_number=circle_acc_number), request.user.member
            if amount < settings.MININIMUM_CIRCLE_SHARES:
                data = {"status":0,"message":"The allowed minimum purchased shares is KES {}".format(settings.MININIMUM_CIRCLE_SHARES)}
                return Response(data,status=status.HTTP_200_OK)
            valid,response = shares_utils.Shares().validate_purchased_shares(amount, circle, member)
            if valid:
                wallet_instance = wallet_utils.Wallet()
                valid,response = wallet_instance.validate_account(request, pin, amount)
                created_objects = []
                shares = None
                if valid:
                    loan_instance = loan_utils.Loan()
                    try:
                        general_instance = general_utils.General()
                        circle_member = CircleMember.objects.get(circle=circle, member=member)
                        shares =circle_member.shares.get()
                        wallet = member.wallet
                        wallet_balance = wallet_instance.calculate_wallet_balance(wallet) - amount
                        transaction_code = general_instance.generate_unique_identifier('WTD')
                        wallet_desc = "{} confirmed.You have purchased shares worth {} {} in circle {}.New wallet balance is {} {}.".format(transaction_code, member.currency, amount, circle.circle_name, member.currency, wallet_balance)
                        wallet_transaction = Transactions.objects.create(wallet=wallet, transaction_type="DEBIT", transaction_time=datetime.datetime.now(), transaction_desc=wallet_desc,transaction_amount=amount, recipient=circle_acc_number, transaction_code=transaction_code, source="shares")
                        created_objects.append(wallet_transaction)
                        print("wallet transaction")
                        print(wallet_transaction.transaction_amount)
                        transaction_code = general_instance.generate_unique_identifier('STD')
                        shares_desc = "{} confirmed.You have purchased shares worth {} {} in circle {}.".format(transaction_code, member.currency, amount, circle.circle_name)
                        shares_transaction = IntraCircleShareTransaction.objects.create(shares=shares, transaction_type="DEPOSIT", sender=circle_member, recipient= circle_member, num_of_shares=amount, transaction_desc=shares_desc, transaction_code=transaction_code)
                        created_objects.append(shares_transaction)
                        print("shares transaction")
                        print(shares_transaction.num_of_shares)
                        shares_utils.Shares().get_circle_member_shares(shares)
                        circle_instance = circle_utils.Circle()
                        available_shares = circle_instance.get_available_circle_member_shares(circle, member)
                        print("available shares")
                        print(available_shares)
                        fcm_available_shares = circle_instance.get_guarantor_available_shares(circle, member)
                        wallet_serializer = WalletTransactionsSerializer(wallet_transaction)
                        shares_serializer = SharesTransactionSerializer(shares_transaction)
                        loan_limit = loan_instance.calculate_loan_limit(circle, member)
                        print("loan limit")
                        print(loan_limit)
                        data = {"status":1, "wallet_transaction":wallet_serializer.data, "shares_transaction":shares_serializer.data, "loan_limit":loan_limit}
                    except Exception as e:
                        print(str(e))
                        shares_utils.Shares().get_circle_member_shares(shares)
                        general_utils.General().delete_created_objects(created_objects)
                        data = {"status":0, "message":"Unable to complete transaction"}
                        return Response(data, status=status.HTTP_200_OK)
                    # unblock task
                    # loan_instance.update_loan_limit(circle,member)
                    updating_loan_limit.delay(circle.id, member.id)
                    fcm_instance = fcm_utils.Fcm()
                    fcm_data = {"request_type":"UPDATE_AVAILABLE_SHARES", "circle_acc_number":circle.circle_acc_number, "phone_number":member.phone_number, "available_shares":fcm_available_shares}
                    registration_id = fcm_instance.get_circle_members_token(circle, member)
                    fcm_instance.data_push("multiple", registration_id, fcm_data)
                    print(fcm_data)
                    return Response(data,status=status.HTTP_200_OK)
                data = {"status":0, "message":response}
                return Response(data, status=status.HTTP_200_OK)
            data = {"status":0, "message":response}
            return Response(data, status=status.HTTP_200_OK)
        data = {"status":0, "message":serializer.errors}
        return Response(data, status=status.HTTP_200_OK)

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
            member = request.user.member
            shares = Shares.objects.get(circle_member=CircleMember.objects.get(circle=circle, member=member))
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
            circle_member = CircleMember.objects.get(member=request.user.member, circle=circle)
            shares = circle_member.shares.get()
            # if circle.circle_name == "umoja":
            #     print("umoja available shares")
            #     available_shares = circle_utils.Circle().get_available_circle_member_shares(circle,request.user.member)
            #     print(available_shares)
            transactions = shares.shares_transaction.all()
            serializer = SharesTransactionSerializer(transactions, many=True, context={'request':request})
            print(serializer.data)
            data = {"status":1, "transactions":serializer.data}
            return Response(data, status=status.HTTP_200_OK)
        data = {"status":0, "message":serializer.errors}
        return Response(data, status=status.HTTP_200_OK)

class SharesWithdrawal(APIView):
    """
    Withdraw shares
    """
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)
    def post(self,request,*args,**kwargs):
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
                    available_shares = circle_instance.get_available_circle_member_shares(circle, member)
                    print("before available_shares")
                    print(available_shares)
                    if amount <= available_shares:
                        shares_tariff = SharesWithdrawalTariff.objects.get(max_amount__gte=amount, min_amount__lte=amount)
                        fcm_available_shares = circle_instance.get_guarantor_available_shares(circle, member)
                        total_amount = amount + shares_tariff.amount
                        if total_amount <= available_shares:
                            if total_amount <= fcm_available_shares:
                                shares = None
                                try:
                                    loan_instance = loan_utils.Loan()
                                    general_instance, wallet_instance = general_utils.General(), wallet_utils.Wallet()
                                    circle_member = CircleMember.objects.get(circle=circle, member=member)
                                    shares = circle_member.shares.get()
                                    time_processed = datetime.datetime.now()
                                    transaction_code = general_instance.generate_unique_identifier('STW')
                                    shares_desc = "%s confirmed.You have withdrawn shares worth %s %s from circle %s.Transaction cost %s %s"%(transaction_code, member.currency, amount, circle.circle_name, member.currency, shares_tariff.amount)
                                    shares_transaction =  IntraCircleShareTransaction.objects.create(shares=shares, transaction_type="WITHDRAW", num_of_shares=total_amount, transaction_desc=shares_desc, transaction_code=transaction_code)
                                    created_objects.append(shares_transaction)
                                    revenue = RevenueStreams.objects.create(stream_amount=shares_tariff.amount,stream_type="SHARES WITHDRAW",stream_code=transaction_code,time_of_transaction=time_processed)
                                    created_objects.append(revenue)
                                    shares_utils.Shares().get_circle_member_shares(shares)
                                    transaction_code = general_instance.generate_unique_identifier('WTC')
                                    wallet_balance = wallet_instance.calculate_wallet_balance(member.wallet) + amount
                                    wallet_desc = "{} confirmed.You have received {} {} from circle {} shares withdrawal.New wallet balance is {} {}".format(transaction_code, member.currency, amount, circle.circle_name, member.currency, wallet_balance)
                                    wallet_transaction = Transactions.objects.create(wallet= member.wallet, transaction_type='CREDIT', transaction_time = time_processed, transaction_desc=wallet_desc, transaction_amount= amount, transaction_code=transaction_code, source="shares")
                                    created_objects.append(wallet_transaction)
                                    shares_transaction_serializer = SharesTransactionSerializer(shares_transaction)
                                    wallet_transaction_serializer = WalletTransactionsSerializer(wallet_transaction)
                                    fcm_available_shares = circle_instance.get_guarantor_available_shares(circle, member)
                                    print("others view of available_shares")
                                    print(fcm_available_shares)
                                    available_shares = circle_instance.get_available_circle_member_shares(circle, member)
                                    print("new available_shares")
                                    print(available_shares)
                                    loan_limit = loan_instance.calculate_loan_limit(circle,member)
                                    print("loan limit")
                                    print(loan_limit)
                                    data = {"status":1, "shares_transaction":shares_transaction_serializer.data, "wallet_transaction":wallet_transaction_serializer.data, "loan_limit":loan_limit, "message":wallet_desc}
                                except Exception as e:
                                    print(str(e))
                                    shares_utils.Shares().get_circle_member_shares(shares)
                                    general_instance = general_utils.General()
                                    general_instance.delete_created_objects(created_objects)
                                    data = {"status":0,"message":"Unable to process the shares withdrawal request"}
                                    return Response(data,status=status.HTTP_200_OK)
                                # unblock task
                                # loan_instance.update_loan_limit(circle,member)
                                updating_loan_limit.delay(circle.id, member.id)
                                fcm_instance = fcm_utils.Fcm()
                                fcm_data = {"request_type":"UPDATE_AVAILABLE_SHARES", "circle_acc_number":circle.circle_acc_number, "phone_number":member.phone_number, "available_shares":fcm_available_shares}
                                registration_id = fcm_instance.get_circle_members_token(circle, member)
                                fcm_instance.data_push("multiple", registration_id, fcm_data)
                                return Response(data,status=status.HTTP_200_OK)
                            data = {"status":0, "message":"Unable to perform shares withdrawal request due pending loan guarantee requests.Kindly response to the requests."}
                            return Response(data, status=status.HTTP_200_OK)
                        data = {"status":0,"message":"Insufficient shares to cover the shares withdrawal charges"}
                        return Response(data,status=status.HTTP_200_OK)
                    data = {"status":0, "message":"Amount entered exceeds your available shares."}
                    return Response(data, status=status.HTTP_200_OK)
                data = {"status":0, "message":response}
                return Response(data, status=status.HTTP_200_OK)
            data = {"status":0, "message":"Invalid pin"}
            return Response(data, status=status.HTTP_200_OK)
        data = {"status":0, "message":serializer.errors}
        return Response(data, status=status.HTTP_200_OK)

@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_shares_withdrawal_tariff(request,*args,**kwargs):
    tariff = SharesWithdrawalTariff.objects.all()
    tariff_serializer = SharesTariffSerializer(tariff,many=True)
    data = {"status":1, "shares_tariff":tariff_serializer.data}
    return Response(data, status=status.HTTP_200_OK)
