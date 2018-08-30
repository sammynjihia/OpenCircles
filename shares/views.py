from django.shortcuts import render
from django.conf import settings
from django.db.models import Sum

from rest_framework.views import APIView
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework import status
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication

from app_utility import wallet_utils, circle_utils, fcm_utils, general_utils, shares_utils, loan_utils, sms_utils, mgr_utils

from .serializers import *
from wallet.serializers import WalletTransactionsSerializer
from shares.serializers import SharesTransactionSerializer

from wallet.models import Transactions, RevenueStreams
from shares.models import IntraCircleShareTransaction, Shares, SharesWithdrawalTariff, MgrCircleTransaction
from circle.models import Circle, CircleMember, MGRCircleCycle, MGRCirclePenalty
from member.models import Member

from loan.tasks import updating_loan_limit

import datetime, uuid

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
    def post(self, request):
        serializer = DepositSerializer(data=request.data)
        if serializer.is_valid():
            pin, amount = serializer.validated_data['pin'], serializer.validated_data['amount']
            circle_acc_number = serializer.validated_data['circle_acc_number']
            circle, member = Circle.objects.get(circle_acc_number=circle_acc_number), request.user.member
            if circle.is_active:
                circle_member = CircleMember.objects.get(circle=circle, member=member)
                if circle_member.is_active:
                    if amount < settings.MIN_SUBSEQUENT_SHARES:
                        data = {"status":0, "message":"The allowed minimum purchased shares is "
                                                      "KES {}".format(settings.MIN_SUBSEQUENT_SHARES)}
                        return Response(data, status=status.HTTP_200_OK)
                    valid,response = shares_utils.Shares().validate_purchased_shares(amount, circle, member)
                    if valid:
                        wallet_instance = wallet_utils.Wallet()
                        valid, response = wallet_instance.validate_account(request, pin, amount)
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
                                wallet_desc = "{} confirmed.You have saved {} {} to circle {}." \
                                              "New wallet balance is {} {}.".format(transaction_code, member.currency,
                                                                                    amount, circle.circle_name,
                                                                                    member.currency, wallet_balance)
                                wallet_transaction = Transactions.objects.create(wallet=wallet, transaction_type="DEBIT",
                                                                                 transaction_time=datetime.datetime.now(),
                                                                                 transaction_desc=wallet_desc,
                                                                                 transaction_amount=amount,
                                                                                 recipient=circle_acc_number,
                                                                                 transaction_code=transaction_code,
                                                                                 source="wallet")
                                created_objects.append(wallet_transaction)
                                print("wallet transaction")
                                print(wallet_transaction.transaction_amount)
                                transaction_code = general_instance.generate_unique_identifier('STD')
                                shares_desc = "{} confirmed.You have saved {} {} " \
                                              "to circle {}.".format(transaction_code, member.currency,
                                                                     amount, circle.circle_name)
                                shares_transaction = IntraCircleShareTransaction.objects.create(shares=shares,
                                                                                                transaction_type="DEPOSIT",
                                                                                                sender=circle_member,
                                                                                                recipient= circle_member,
                                                                                                num_of_shares=amount,
                                                                                                transaction_desc=shares_desc,
                                                                                                transaction_code=transaction_code)
                                created_objects.append(shares_transaction)
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
                                data = {"status":1,
                                        "wallet_transaction":wallet_serializer.data,
                                        "shares_transaction":shares_serializer.data,
                                        "loan_limit":loan_limit}
                            except Exception as e:
                                print(str(e))
                                general_utils.General().delete_created_objects(created_objects)
                                data = {"status":0, "message":"Unable to complete transaction"}
                                return Response(data, status=status.HTTP_200_OK)
                            # unblock task
                            # loan_instance.update_loan_limit(circle,member)
                            updating_loan_limit.delay(circle.id, member.id)
                            fcm_instance = fcm_utils.Fcm()
                            fcm_data = {"request_type":"UPDATE_AVAILABLE_SHARES",
                                        "circle_acc_number":circle.circle_acc_number,
                                        "phone_number":member.phone_number,
                                        "available_shares":fcm_available_shares}
                            registration_id = fcm_instance.get_circle_members_token(circle, member)
                            fcm_instance.data_push("multiple", registration_id, fcm_data)
                            print(fcm_data)
                            return Response(data,status=status.HTTP_200_OK)
                        data = {"status":0, "message":response}
                        return Response(data, status=status.HTTP_200_OK)
                data = {"status":0,"message":"Unable to deposit to circle.Your account is currently deactivated due"
                                             " to delayed loan repayment."}
                return Response(data, status=status.HTTP_200_OK)
            data = {"status":0, "message":"Unable to deposit to circle.Circle is inactive."}
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

    def post(self,request):
        serializer = MemberSharesSerializer(data=request.data)
        if serializer.is_valid():
            circle_acc = serializer.validated_data['circle_acc_number']
            circle = Circle.objects.get(circle_acc_number = circle_acc)
            member = request.user.member
            shares = Shares.objects.get(circle_member=CircleMember.objects.get(circle=circle, member=member))
            shares_serializer = SharesSerializer(shares)
            data = {"status":1, "shares":shares_serializer.data}
            return Response(data, status=status.HTTP_200_OK)
        data = {"status":0, "message":serializer.errors}
        return Response(data, status=status.HTTP_200_OK)

class MemberSharesTransactions(APIView):
    """
    Fetches transactions for member
    """
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)

    def post(self,request):
        serializer = MemberSharesSerializer(data=request.data)
        if serializer.is_valid():
            circle_acc = serializer.validated_data['circle_acc_number']
            circle = Circle.objects.get(circle_acc_number=circle_acc)
            try:
                circle_member = CircleMember.objects.get(member=request.user.member, circle=circle)
            except CircleMember.DoesNotExist:
                data = {"status": 0, "message": "Unable to fetch shares transaction"}
                return Response(data, status=status.HTTP_200_OK)
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
    def post(self,request):
        serializer = SharesWithdrawalSerializer(data=request.data)
        if serializer.is_valid():
            pin = serializer.validated_data['pin']
            circle = Circle.objects.get(circle_acc_number=serializer.validated_data['circle_acc_number'])
            member = request.user.member
            created_objects = []
            if circle.is_active:
                circle_member = CircleMember.objects.get(circle=circle, member=member)
                if circle_member.is_active:
                    if request.user.check_password(pin):
                        amount = serializer.validated_data['amount']
                        valid,response = shares_utils.Shares().validate_withdrawal_amount(amount)
                        if valid:
                            circle_instance = circle_utils.Circle()
                            available_shares = circle_instance.get_available_circle_member_shares(circle, member)
                            print("before available_shares")
                            print(available_shares)
                            if amount <= available_shares:
                                shares_tariff = SharesWithdrawalTariff.objects.get(max_amount__gte=amount,
                                                                                   min_amount__lte=amount)
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
                                            shares_desc = "{} confirmed.You have withdrawn shares worth {} {} from " \
                                                          "circle {}.Transaction cost {} {}".format(transaction_code,
                                                                                                    member.currency,
                                                                                                    amount,
                                                                                                    circle.circle_name,
                                                                                                    member.currency,
                                                                                                    shares_tariff.amount)
                                            shares_transaction =  IntraCircleShareTransaction.objects.create(
                                                                                                        shares=shares,
                                                                                                        transaction_type="WITHDRAW",
                                                                                                        num_of_shares=total_amount,
                                                                                                        transaction_desc=shares_desc,
                                                                                                        transaction_code=transaction_code)
                                            created_objects.append(shares_transaction)
                                            revenue = RevenueStreams.objects.create(stream_amount=shares_tariff.amount,
                                                                                    stream_type="SHARES WITHDRAW",
                                                                                    stream_code=transaction_code,
                                                                                    time_of_transaction=time_processed)
                                            created_objects.append(revenue)
                                            transaction_code = general_instance.generate_unique_identifier('WTC')
                                            wallet_balance = wallet_instance.calculate_wallet_balance(member.wallet) + amount
                                            wallet_desc = "{} confirmed.You have received {} {} from circle {} shares " \
                                                          "withdrawal.New wallet balance is {} {}".format(transaction_code,
                                                                                                          member.currency,
                                                                                                          amount,
                                                                                                          circle.circle_name,
                                                                                                          member.currency,
                                                                                                          wallet_balance)
                                            wallet_transaction = Transactions.objects.create(wallet= member.wallet,
                                                                                             transaction_type='CREDIT',
                                                                                             transaction_time=time_processed,
                                                                                             transaction_desc=wallet_desc,
                                                                                             transaction_amount=amount,
                                                                                             transaction_code=transaction_code,
                                                                                             source="shares")
                                            created_objects.append(wallet_transaction)
                                            shares_transaction_serializer = SharesTransactionSerializer(shares_transaction)
                                            wallet_transaction_serializer = WalletTransactionsSerializer(wallet_transaction)
                                            fcm_available_shares = circle_instance.get_guarantor_available_shares(circle, member)
                                            print("others view of available_shares")
                                            print(fcm_available_shares)
                                            available_shares = circle_instance.get_available_circle_member_shares(circle, member)
                                            print("new available_shares")
                                            print(available_shares)
                                            loan_limit = loan_instance.calculate_loan_limit(circle, member)
                                            print("loan limit")
                                            print(loan_limit)
                                            data = {"status":1,
                                                    "shares_transaction":shares_transaction_serializer.data,
                                                    "wallet_transaction":wallet_transaction_serializer.data,
                                                    "loan_limit":loan_limit,
                                                    "message":wallet_desc}
                                        except Exception as e:
                                            print(str(e))
                                            general_instance = general_utils.General()
                                            general_instance.delete_created_objects(created_objects)
                                            data = {"status":0, "message":"Unable to process the shares withdrawal request"}
                                            return Response(data, status=status.HTTP_200_OK)
                                        # unblock task
                                        # loan_instance.update_loan_limit(circle,member)
                                        updating_loan_limit.delay(circle.id, member.id)
                                        fcm_instance = fcm_utils.Fcm()
                                        fcm_data = {"request_type":"UPDATE_AVAILABLE_SHARES",
                                                    "circle_acc_number":circle.circle_acc_number,
                                                    "phone_number":member.phone_number,
                                                    "available_shares":fcm_available_shares}
                                        registration_id = fcm_instance.get_circle_members_token(circle, member)
                                        fcm_instance.data_push("multiple", registration_id, fcm_data)
                                        return Response(data, status=status.HTTP_200_OK)
                                    data = {"status":0, "message":"Unable to perform shares withdrawal request due to"
                                                                  " pending loan guarantee requests."
                                                                  "Kindly response to the requests."}
                                    return Response(data, status=status.HTTP_200_OK)
                                data = {"status":0, "message":"Insufficient shares to cover the shares withdrawal charges"}
                                return Response(data, status=status.HTTP_200_OK)
                            data = {"status":0, "message":"Amount entered exceeds your available shares."}
                            return Response(data, status=status.HTTP_200_OK)
                        data = {"status":0, "message":response}
                        return Response(data, status=status.HTTP_200_OK)
                    data = {"status":0, "message":"Invalid pin"}
                    return Response(data, status=status.HTTP_200_OK)
                data = {"status":0, "message":"Unable to withdraw savings from circle. Your account is currently "
                                             "deactivated due to delayed loan repayment."}
                return Response(data, status=status.HTTP_200_OK)
            data = {"status":0, "message":"Unable to withdraw savings from circle.Circle is inactive."}
        data = {"status":0, "message":serializer.errors}
        return Response(data, status=status.HTTP_200_OK)

@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_shares_withdrawal_tariff(request):
    tariff = SharesWithdrawalTariff.objects.all()
    tariff_serializer = SharesTariffSerializer(tariff, many=True)
    data = {"status":1, "shares_tariff":tariff_serializer.data}
    return Response(data, status=status.HTTP_200_OK)

@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_circle_member_shares_transactions(request):
    serializer = CircleMemberTransactionSerializer(data=request.data)
    if serializer.is_valid():
        circle_acc_number = serializer.validated_data['circle_acc_number']
        phone_number = sms_utils.Sms().format_phone_number(serializer.validated_data['phone_number'])
        member = Member.objects.get(phone_number=phone_number)
        circle = Circle.objects.get(circle_acc_number=circle_acc_number)
        circle_member = CircleMember.objects.get(member=member, circle=circle)
        shares = circle_member.shares.get()
        transactions = shares.shares_transaction.all()
        serializer = SharesTransactionSerializer(transactions, many=True)
        print(serializer.data)
        data = {"status": 1, "transactions": serializer.data}
        return Response(data, status=status.HTTP_200_OK)
    data = {"status":0, "message":serializer.errors}
    return Response(data, status=status.HTTP_200_OK)

class MgrContribution(APIView):
    """
    Endpoint for mgr contributions
    """
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        serializer = DepositSerializer(data=request.data)
        if serializer.is_valid():
            amount = serializer.validated_data['amount']
            pin = serializer.validated_data['pin']
            circle_acc_number = serializer.validated_data['circle_acc_number']
            circle = Circle.objects.get(circle_acc_number=circle_acc_number)
            mgr_circle = circle.mgr_circle.get()
            member = request.user.member
            circle_member = CircleMember.objects.get(circle=circle, member=member)
            wallet_instance = wallet_utils.Wallet()
            mgr_instance = mgr_utils.MerryGoRound()
            penalty_amount = mgr_utils.MerryGoRound().get_circle_member_penalty_amount(circle_member)
            include_penalty = True if penalty_amount > 0 else False
            if include_penalty:
                data_response = mgr_instance.cycle_join_status(circle_member)
                join_status = data_response['join_cycle']
                print("join_status")
                print(join_status)
                expected_total = penalty_amount + mgr_circle.amount if join_status else penalty_amount
                is_contribution = True if join_status else False
                print("is_contribution")
                print(is_contribution)

            else:
                if not circle.is_active:
                    data = {"status": 0, "message": "Unable to perform transaction. Circle is currently deactivated."}
                    return Response(data, status=status.HTTP_200_OK)
                res, data = mgr_instance.validate_circle_member_contribution(circle_member)
                if not res:
                    return Response(data, status=status.HTTP_200_OK)
                expected_total = mgr_circle.amount
                is_contribution = True

            if amount != expected_total:
                #to_do: edit msg
                msg = "Unable to process transaction. You are to contribute {} {} not {} {}".format(member.currency,
                                                                                                    expected_total,
                                                                                                    member.currency,
                                                                                                    amount)
                data = {"status": 0, "message": msg}
                return Response(data, status=status.HTTP_200_OK)

            valid, response = wallet_instance.validate_account_info(request, amount, pin, None)
            if valid:
                general_instance = general_utils.General()
                created_objects = []
                try:
                    contribution = {}
                    wallet = member.wallet
                    wallet_balance = wallet_instance.calculate_wallet_balance(wallet) - amount
                    transaction_code = general_instance.generate_unique_identifier('WTD')
                    wallet_desc = "{} confirmed. You have contributed {} {} to circle {}." \
                                  "New wallet balance is {} {}.".format(transaction_code, member.currency,
                                                                        amount, circle.circle_name,
                                                                        member.currency, wallet_balance)
                    wallet_transaction = Transactions.objects.create(wallet=wallet, transaction_type="DEBIT",
                                                                     transaction_time=datetime.datetime.now(),
                                                                     transaction_desc=wallet_desc,
                                                                     transaction_amount=amount,
                                                                     recipient=circle_acc_number,
                                                                     transaction_code=transaction_code,
                                                                     source="wallet")
                    print("wallet_transaction")
                    print(wallet_transaction)
                    created_objects.append(wallet_transaction)
                    if is_contribution:
                        circle_cycle = MGRCircleCycle.objects.filter(circle_member__circle=circle).latest('id')
                        transaction_code = transaction_code.replace('WTD', 'CTD')
                        transaction_desc = "{} confirmed. You have contributed {} {}.".format(transaction_code,
                                                                                              member.currency,
                                                                                              mgr_circle.amount)
                        contribution = MgrCircleTransaction.objects.create(circle_member=circle_member,
                                                                           transaction_type="DEPOSIT",
                                                                           amount=mgr_circle.amount,
                                                                           transaction_code=transaction_code,
                                                                           transaction_desc=transaction_desc,
                                                                           transaction_time=datetime.datetime.now(),
                                                                           cycle=circle_cycle)
                        created_objects.append(contribution)
                        contribution_serializer = AdminContributionsTransactionSerializer(contribution)
                        print(contribution_serializer.data)
                        admin_contribution = contribution_serializer.data
                        member_contribution_serializer = ContributionsTransactionSerializer(contribution)
                        contribution = member_contribution_serializer.data
                    if include_penalty:
                        #to_do:celerify
                        mgr_instance.process_paid_penalties(circle_member)
                        mgr_instance.reinstate_defaulted_circle_member(circle_member, join_status)

                    wallet_serializer = WalletTransactionsSerializer(wallet_transaction)
                    if is_contribution:
                        print('here')
                        fcm_instance = fcm_utils.Fcm()
                        registration_ids = fcm_instance.get_circle_admins_tokens(circle)
                        print(registration_ids)
                        if len(registration_ids):
                            fcm_data = {"request_type": "UPDATE_MGR_CONTRIBUTION",
                                        "contribution": admin_contribution}
                            fcm_instance.data_push("multiple", registration_ids, fcm_data)
                    data = {"status":1, "wallet_transaction":wallet_serializer.data,
                            "contribution":contribution}
                    return Response(data, status=status.HTTP_200_OK)

                except Exception as e:
                    print(str(e))
                    general_instance.delete_created_objects(created_objects)
                    data = {"status":0, "message":"Unable to process transaction."}
                    return Response(data, status=status.HTTP_200_OK)

            data = {"status": 0, "message": response}
            return Response(data, status=status.HTTP_200_OK)
        data = {"status":0, "message":serializer.errors}
        return Response(data, status=status.HTTP_200_OK)

class MgrContributionDisbursal(APIView):
    """
    contribution disbursal endpoint
    """
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)
    def post(self, request):
        serializer = ContributionCircleAccSerializer(data=request.data)
        if serializer.is_valid():
            circle_acc_number = serializer.validated_data['circle_acc_number']
            circle = Circle.objects.get(circle_acc_number=circle_acc_number)
            try:
                circle_member = CircleMember.objects.get(circle=circle, member=request.user.member)
            except CircleMember.DoesNotExist:
                data = {"status":0, "message":"User is not a member for this circle"}
                return Response(data, status=status.HTTP_200_OK)
            if circle_member.is_admin:
                created_objects = []
                general_instance = general_utils.General()
                try:
                    circle_cycle = MGRCircleCycle.objects.get(circle_member__circle=circle, is_complete=False)
                    delta = datetime.date.today() - circle_cycle.disbursal_date
                    if delta.days < 0:
                        data = {"status": 0, "message": "Unable to disburse contributions. Time for disbursal is not due"}
                        return Response(data, status=status.HTTP_200_OK)

                except MGRCircleCycle.DoesNotExist:
                    data = {"status": 0, "message": "Unable to disburse contributions."}
                    return Response(data, status=status.HTTP_200_OK)

                try:
                    recipient = circle_cycle.circle_member
                    transaction_amount = MgrCircleTransaction.objects.filter(circle_member__circle=circle,
                                                                             cycle=circle_cycle).aggregate(total_amount=Sum('amount'))
                    transaction_amount = transaction_amount['total_amount'] if transaction_amount['total_amount'] is not None else 0
                    print(transaction_amount)
                    if transaction_amount > 0:
                        #to_do:appy tariff for MGR withdrawal
                        transaction_cost = SharesWithdrawalTariff.objects.get(max_amount__gte=transaction_amount,
                                                                              min_amount__lte=transaction_amount).amount
                        actual_amount = transaction_amount - transaction_cost
                        wallet_instance = wallet_utils.Wallet()
                        transaction_code = general_instance.generate_unique_identifier('CTW')
                        transaction_desc = "{} confirmed. KES {} has been sent to {}.".format(transaction_code,
                                                                                              transaction_amount,
                                                                                              recipient.member.phone_number)
                        total_contribution = mgr_utils.MerryGoRound().get_mgr_circle_total_contributions(circle)
                        if total_contribution >= transaction_amount:
                            contributions_trx = MgrCircleTransaction.objects.create(transaction_code=transaction_code,
                                                                                    amount=transaction_amount,
                                                                                    transaction_type="WITHDRAW",
                                                                                    transaction_time=datetime.datetime.now(),
                                                                                    transaction_desc=transaction_desc,
                                                                                    circle_member=recipient,
                                                                                    cycle=circle_cycle)
                        else:
                            msg = "Unable to disburse contribution of KES {}. " \
                                  "Insufficient contributions".format(transaction_amount)
                            data = {"status": 0, "message": msg}
                            return Response(data, status=status.HTTP_200_OK)
                        created_objects.append(contributions_trx)
                        transaction_code = transaction_code.replace('CTW', 'WTC')
                        wallet_balance = wallet_instance.calculate_wallet_balance(recipient.member.wallet) + actual_amount
                        wallet_desc = "{} confirmed. You have received {} {} from circle {}. " \
                                      "New wallet balance is {} {}".format(transaction_code,
                                                                           recipient.member.currency,
                                                                           actual_amount,
                                                                           circle.circle_name,
                                                                           recipient.member.currency,
                                                                           wallet_balance)
                        wallet_transaction = Transactions.objects.create(wallet=recipient.member.wallet,
                                                                         transaction_code=transaction_code,
                                                                         transaction_amount=actual_amount,
                                                                         transaction_type="CREDIT",
                                                                         transaction_time=datetime.datetime.now(),
                                                                         transaction_desc=wallet_desc,
                                                                         source="contribution",
                                                                         transacted_by=circle.circle_acc_number
                                                                         )
                        created_objects.append(wallet_transaction)
                        wallet_serializer = WalletTransactionsSerializer(wallet_transaction)
                        contribution_serializer = AdminContributionsTransactionSerializer(contributions_trx)
                        circle_cycle.is_complete = True
                        circle_cycle.save()
                        mgr_instance = mgr_utils.MerryGoRound()
                        print('hapa1')
                        mgr_instance.penalize_circle_members(circle_cycle, created_objects)
                        fcm_instance = fcm_utils.Fcm()
                        fcm_data = {"request_type":"CREDIT_WALLET",
                                    "wallet_transaction":wallet_serializer.data}
                        fcm_instance.data_push('single', recipient.member.device_token, fcm_data)
                        data = {"status":1,
                                "contribution":contribution_serializer.data,
                                }
                        return Response(data, status=status.HTTP_200_OK)
                    data = {"status":0, "message":"Unable to disburse contribution of KES 0"}
                    return Response(data, status=status.HTTP_200_OK)

                except Exception as e:
                    print(str(e))
                    general_instance.delete_created_objects(created_objects)
                    circle_cycle.is_complete = False
                    circle_cycle.save()
                    data = {"status":0, "message":"Unable to disburse contribution."}
                    return Response(data, status=status.HTTP_200_OK)

            data = {"status":0, "message":"Unauthorized access."}
            return Response(data, status=status.HTTP_200_OK)
        data = {"status":0, "message":serializer.errors}
        return Response(data, status=status.HTTP_200_OK)

@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_circle_members_contributions(request):
    serializer = ContributionCircleAccSerializer(data=request.data)
    if serializer.is_valid():
        circle = Circle.objects.get(circle_acc_number=serializer.validated_data['circle_acc_number'])
        member = request.user.member
        try:
            try:
                circle_member = CircleMember.objects.get(circle=circle, member=member)

            except CircleMember.DoesNotExist:
                msg = "Unable to fetch contributions"
                data = {"status":0, "message":msg}
                return Response(data, status=status.HTTP_200_OK)

            if not circle_member.is_admin:
                msg = "Unauthorized access."
                data = {"status": 0, "message": msg}
                return Response(data, status=status.HTTP_200_OK)

            contributions = MgrCircleTransaction.objects.filter(circle_member__circle=circle)
            contribution_serializer = AdminContributionsTransactionSerializer(contributions, many=True)
            data = {"status": 1, "contributions": contribution_serializer.data}
            return Response(data, status=status.HTTP_200_OK)

        except Exception as e:
            print(str(e))
            msg = "Unable to fetch contributions"
            data = {"status": 0, "message": msg}
            return Response(data, status=status.HTTP_200_OK)

    data = {"status":0, "message":serializer.errors}
    return Response(data, status=status.HTTP_200_OK)

@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_circle_members_trxs(request):
    serializer = ContributionCircleAccSerializer(data=request.data)
    if serializer.is_valid():
        try:
            circle_acc_number = serializer.validated_data['circle_acc_number']
            circle = Circle.objects.get(circle_acc_number=circle_acc_number, circle_model_type="Savings and Loans")
            try:
                CircleMember.objects.get(circle=circle, member=request.user.member, is_admin=True)
                shares_trx = IntraCircleShareTransaction.objects.filter(shares__circle_member__circle=circle).\
                    values('shares__circle_member__member__phone_number').annotate(total=Sum('num_of_shares')).\
                    filter(transaction_type='DEPOSIT').annotate(total_deposits=Sum('num_of_shares'))

            except CircleMember.DoesNotExist:
                data = {"status":0, "message":"Unauthorized access."}

        except Circle.DoesNotExist:
            data = {"status":0, "message":"Unable to complete process."}

        return Response(data, status=status.HTTP_200_OK)

    data = {"status":0, "message":serializer.errors}
    return Response(data, status=status.HTTP_200_OK)

@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def get_circle_member_defaulted_contributions(request):
    serializer = ContributionCircleAccSerializer(data=request.data)
    if serializer.is_valid():
        circle = Circle.objects.get(circle_acc_number=serializer.validated_data['circle_acc_number'])
        member = request.user.member
        try:
            circle_member = CircleMember.objects.get(circle=circle, member=member)
            penalties = MGRCirclePenalty.objects.filter(circle_member=circle_member)
            penalty_serializer = CircleMemberPenalties(penalties, many=True)
            data = {"status":1, "penalties":penalty_serializer.data}

        except CircleMember.DoesNotExist:
            data = {"status":0, "message":"Your are not a member of this circle"}

        return Response(data, status=status.HTTP_200_OK)

    data = {"status":0, "message":serializer.errors}
    return Response(data, status=status.HTTP_200_OK)