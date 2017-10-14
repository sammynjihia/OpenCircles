from __future__ import division

from django.shortcuts import render
from django.db.models import Q
from django.conf import settings

from .serializers import *
from wallet.serializers import WalletTransactionsSerializer
from shares.serializers import SharesTransactionSerializer

from rest_framework.views import APIView
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view,authentication_classes,permission_classes
from rest_framework.reverse import reverse

from circle.models import Circle,CircleMember
from member.models import Member
from shares.models import LockedShares,IntraCircleShareTransaction,UnlockedShares
from wallet.models import Transactions
from loan.models import LoanApplication as loanapplication,GuarantorRequest,LoanAmortizationSchedule,LoanRepayment as loanrepayment,LoanGuarantor

from app_utility import general_utils,fcm_utils,circle_utils,wallet_utils,loan_utils,sms_utils

import datetime,json,math,uuid

# Create your views here.

@api_view(['GET'])
def api_root(request,format=None):
    return Response({
                        "loan_application":reverse('loan_application',request=request,format=format),
                        "loan list":reverse('my_loans', request=request, format=format)
    })


class LoanApplication(APIView):
    """
    Applies for loan
    """
    authentication_classes = (TokenAuthentication, )
    permission_classes = (IsAuthenticated, )

    def post(self, request, *args, **kwargs):
        if 'guarantors' in request.data:
            mutable = request.data._mutable
            request.data._mutable = True
            request.data['guarantors'] = json.loads(request.data['guarantors'])
            request.data._mutable = mutable
        serializer = LoanApplicationSerializer(data=request.data)
        if serializer.is_valid():
            created_objects = []
            pin = serializer.validated_data['pin']
            loan_amount = serializer.validated_data['loan_amount']
            guarantors = serializer.validated_data['guarantors']
            circle = Circle.objects.get(circle_acc_number=serializer.validated_data['circle_acc_number'])
            if request.user.check_password(pin):
                loan_instance = loan_utils.Loan()
                valid,response = loan_instance.validate_loan_amount(request,loan_amount,circle)
                if valid:
                    member=request.user.member
                    circle_member = CircleMember.objects.get(circle=circle,member=member)
                    circle_loan_code = "LN{}".format(circle.circle_acc_number)
                    loans = loanapplication.objects.filter(loan_code__startswith = circle_loan_code)
                    if loans.exists():
                        latest_loan = loans.latest('id')
                        value = latest_loan.loan_code[len(circle_loan_code):]
                        new_value = int(value) + 1
                        new_value = str(new_value)
                        value = new_value if len(new_value)>1 else new_value.zfill(2)
                        loan_code = circle_loan_code+value
                    else:
                        loan_code = circle_loan_code+"01"
                    try:
                        loan_tariff = LoanTariff.objects.get(Q(max_amount__gte=loan_amount) & Q(min_amount__lte=loan_amount) & Q(circle=circle))
                    except LoanTariff.DoesNotExist:
                        data = {"status":0,"message":"Unable to process loan.The circle has no loan tariff."}
                        return Response(data,status=status.HTTP_200_OK)
                    annual_interest_rate =  loan_tariff.monthly_interest_rate * 12
                    loan = loanapplication.objects.create(loan_code=loan_code,circle_member=circle_member,amount=loan_amount,interest_rate=loan_tariff.monthly_interest_rate,num_of_repayment_cycles=loan_tariff.num_of_months)
                    created_objects.append(loan)
                    guarantors = guarantors[0]
                    shares_desc = "Shares worth {} {} locked to guarantee loan".format(member.currency,loan_amount)
                    shares = circle_member.shares.get()
                    circle_instance = circle_utils.Circle()
                    available_shares =  circle_instance.get_available_circle_member_shares(circle,member)
                    print(available_shares)
                    if loan_amount > available_shares:
                        if len(guarantors):
                            try:
                                guaranteed_loan = loan_amount - available_shares
                                print(guaranteed_loan)
                                guarantor_objs = [ GuarantorRequest(loan=loan,
                                                                    circle_member=CircleMember.objects.get(
                                                                                    member=Member.objects.get(phone_number=guarantor["phone_number"]),circle=circle),
                                                                    num_of_shares=guarantor["amount"], time_requested=datetime.datetime.today(),fraction_guaranteed=guarantor["amount"]/guaranteed_loan
                                                                    ) for guarantor in guarantors]
                                loan_guarantors = GuarantorRequest.objects.bulk_create(guarantor_objs)
                                shares_transaction = IntraCircleShareTransaction.objects.create(shares=shares,transaction_type="LOCKED",num_of_shares=available_shares,transaction_desc=shares_desc,transaction_code="ST"+uuid.uuid1().hex[:10].upper())
                                created_objects.append(shares_transaction)
                                locked_shares = LockedShares.objects.create(shares_transaction=shares_transaction,loan=loan)
                                created_objects.append(locked_shares)
                                available_shares = circle_instance.get_available_circle_member_shares(circle,member)
                                print(available_shares)
                                loan_limit = available_shares+settings.LOAN_LIMIT
                                print(loan_limit)
                                shares_transaction_serializer = SharesTransactionSerializer(shares_transaction)
                                print(shares_transaction_serializer.data)
                                print(loan_guarantors)
                                loan_guarantors_serializer = LoanGuarantorsSerializer(loan_guarantors,many=True)
                                loan_serializer = LoansSerializer(loan)
                                data = {"status":1,"shares_transaction":shares_transaction_serializer.data,"message":"Loan application successfully received.Waiting for guarantors approval","loan":loan_serializer.data,"loan_limit":loan_limit,"loan_guarantors":loan_guarantors_serializer.data}
                                instance = fcm_utils.Fcm()
                                for guarantor in loan_guarantors:
                                    guarantor_member = guarantor.circle_member.member
                                    guarantor_available_shares = circle_instance.get_guarantor_available_shares(circle,guarantor_member)
                                    fcm_data = {"request_type":"UPDATE_AVAILABLE_SHARES","circle_acc_number":circle.circle_acc_number,"phone_number":guarantor_member.phone_number,"available_shares":guarantor_available_shares}
                                    registration_ids = instance.get_circle_members_token(circle,guarantor_member)
                                    instance.data_push("multiple",registration_ids,fcm_data)
                                    fcm_data = {"request_type":"GUARANTEE_LOAN_REQUEST","phone_number":member.phone_number,"circle_acc_number":circle.circle_acc_number,"loan_code":loan.loan_code,"amount":guarantor.num_of_shares,"num_of_months":loan_tariff.num_of_months,"rating":30,"estimated_earning":500}
                                    registration_id = guarantor_member.device_token
                                    instance.data_push("single",registration_id,fcm_data)
                                    title = circle.circle_name
                                    adverb = "her" if member.gender == "F" or member.gender == "Female" else "him"
                                    message = "%s %s has requested you to guarantee %s kes %s "%(member.user.first_name,member.user.last_name,adverb,guarantor.num_of_shares)
                                    instance.notification_push("single",registration_id,title,message)
                                fcm_data = {"request_type":"UPDATE_AVAILABLE_SHARES","circle_acc_number":circle.circle_acc_number,"phone_number":member.phone_number,"available_shares":available_shares}
                                registration_id = instance.get_circle_members_token(circle,member)
                                instance.data_push("multiple",registration_id,fcm_data)
                                return Response(data, status=status.HTTP_200_OK)
                            except Exception as e:
                                print(str(e))
                                instance = general_utils.General()
                                instance.delete_created_objects(created_objects)
                                data = {"status": 0, "message":"Unable to process loan"}
                                return Response(data, status=status.HTTP_200_OK)
                        data = {"status":0,"message":"Loan can not be processed.Guarantors needed"}
                        return Response(data,status=status.HTTP_200_OK)
                    try:
                        shares_transaction = IntraCircleShareTransaction.objects.create(shares=shares,transaction_type="LOCKED",num_of_shares=loan_amount,transaction_desc=shares_desc,transaction_code="ST"+uuid.uuid1().hex[:10].upper())
                        created_objects.append(shares_transaction)
                        locked_shares = LockedShares.objects.create(shares_transaction=shares_transaction,loan=loan)
                        created_objects.append(locked_shares)
                        wallet_desc = "Credited wallet with loan worth {} {}".format(member.currency,loan_amount)
                        wallet_transaction = Transactions.objects.create(wallet= member.wallet, transaction_type='CREDIT', transaction_time = datetime.datetime.now(),transaction_desc=wallet_desc, transaction_amount= loan_amount, transacted_by = circle.circle_name,transaction_code="WT"+uuid.uuid1().hex[:10].upper())
                        created_objects.append(wallet_transaction)
                        loan.is_approved=True
                        loan.is_disbursed=True
                        loan.time_disbursed=datetime.datetime.now()
                        loan.time_approved=datetime.datetime.now()
                        loan.save()
                        wallet_transaction_serializer = WalletTransactionsSerializer(wallet_transaction)
                        shares_transaction_serializer = SharesTransactionSerializer(shares_transaction)
                        loan_serializer = LoansSerializer(loan)
                        shares_instance = circle_utils.Circle()
                        available_shares = shares_instance.get_available_circle_member_shares(circle,member)
                        loan_limit = available_shares + settings.LOAN_LIMIT
                        loan_amortization = loan_instance.amortization_schedule(annual_interest_rate, loan_amount,loan_tariff.num_of_months, loan.time_approved.date())
                        loan_amortization['loan'] = loan
                        loan_amortization_schedule = LoanAmortizationSchedule(**loan_amortization)
                        loan_amortization_schedule.save()
                        created_objects.append(loan_amortization_schedule)
                        message = "Your loan of {} {} has been successfully processed.Your wallet has been credited with kes {}".format(member.currency,loan_amount,loan_amount)
                        full_amortization_schedule = json.dumps(loan_instance.full_amortization_schedule(annual_interest_rate, loan_amount,loan_tariff.num_of_months, loan.time_approved.date()))
                        data = {"status":1,"loan":loan_serializer.data,"wallet_transaction":wallet_transaction_serializer.data,"shares_transaction":shares_transaction_serializer.data,"loan_limit":loan_limit,"full_amortization_schedule":full_amortization_schedule,"message":message}
                        instance = fcm_utils.Fcm()
                        fcm_data = {"request_type":"UPDATE_AVAILABLE_SHARES","circle_acc_number":circle.circle_acc_number,"phone_number":member.phone_number,"available_shares":available_shares}
                        registration_id = instance.get_circle_members_token(circle,member)
                        instance.data_push("multiple",registration_id,fcm_data)
                        return Response(data, status=status.HTTP_200_OK)
                    except Exception as e:
                        print(str(e))
                        instance = general_utils.General()
                        instance.delete_created_objects(created_objects)
                        data = {"status": 0, "message":"Unable to process loan"}
                        return Response(data, status=status.HTTP_200_OK)
                data = {"status":0,"message":response}
                return Response(data,status=status.HTTP_200_OK)
            data = {"status":0,"message":"Incorrect pin"}
            return Response(data,status=status.HTTP_200_OK)
        data = {"status":0,"message":serializer.errors}
        return Response(data,status=status.HTTP_200_OK)

class LoanRepayment(APIView):
    """
    Captures loans repayed
    """
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)
    def post(self,request,*args,**kwargs):
        serializer = LoanRepaySerializer(data=request.data)
        if serializer.is_valid():
            wallet_instance = wallet_utils.Wallet()
            repayment_amount,pin = serializer.validated_data['amount'],serializer.validated_data['pin']
            valid,response = wallet_instance.validate_account(request,pin,repayment_amount)
            user = request.user
            if valid:
                created_objects = []
                loan = loanapplication.objects.get(loan_code=serializer.validated_data['loan_code'])
                if not loan.is_fully_repaid:
                    loan_amortize = LoanAmortizationSchedule.objects.filter(loan=loan)
                    loan_instance = loan_utils.Loan()
                    if not loan_amortize.exists():
                        data = {"status":0,"message":"Unable to process the loan repayment request."}
                        return Response(data,status=status.HTTP_200_OK)
                    latest_loan_amortize = loan_amortize.latest('id')
                    valid,response = loan_instance.validate_repayment_amount(repayment_amount,latest_loan_amortize)
                    if valid:
                        circle = loan.circle_member.circle
                        loan_repayment = loan_amortize.filter(~Q(loan_repayment=None)).count()
                        print(loan_amortize.filter().values_list('loan_repayment'))
                        loan_tariff = LoanTariff.objects.get(circle=circle,max_amount__gte=loan.amount,min_amount__lte=loan.amount)
                        paid_months = loan_repayment + 1
                        print("paid months")
                        print(paid_months)
                        remaining_number_of_months = loan_tariff.num_of_months - paid_months
                        print("remaining months")
                        print(remaining_number_of_months)
                        annual_interest_rate = loan_tariff.monthly_interest_rate * 12
                        if repayment_amount > latest_loan_amortize.total_repayment and remaining_number_of_months == 0:
                            msg = "The amount entered exceeds this month's loan repayment amount of kes {}".format(latest_loan_amortize.total_repayment)
                            data = {"status":0,"message":msg}
                            return Response(data,status=status.HTTP_200_OK)
                        try:
                            wallet_desc = "Kes {} sent to circle {} for loan repayment".format(repayment_amount,circle.circle_name)
                            time_processed = datetime.datetime.now()
                            wallet_transaction = Transactions.objects.create(wallet = user.member.wallet,transaction_type="DEBIT",transaction_desc=wallet_desc,recipient=circle.circle_acc_number,transaction_amount=repayment_amount,transaction_time=time_processed,transaction_code="WT"+uuid.uuid1().hex[:10].upper())
                            created_objects.append(wallet_transaction)
                            loan_repayment = loanrepayment.objects.create(amount=repayment_amount,time_of_repayment=time_processed,amortization_schedule=latest_loan_amortize)
                            created_objects.append(loan_repayment)
                            guarantors = GuarantorRequest.objects.filter(loan=loan,unlocked=False)
                            extra_principal = repayment_amount - latest_loan_amortize.total_repayment
                            ending_balance = math.ceil(latest_loan_amortize.ending_balance) - extra_principal
                            if guarantors.exists():
                                unlockable = loan_instance.calculate_total_paid_principal(loan)
                                if unlockable:
                                    #unblock unlock guarantor shares
                                    loan_instance.unlock_guarantors_shares(guarantors)
                            wallet_transaction_serializer = WalletTransactionsSerializer(wallet_transaction)
                            circle_instance = circle_utils.Circle()
                            if remaining_number_of_months == 0 or ending_balance == 0:
                                shares_desc = "Shares worth {} {} unlocked".format(user.member.currency,loan.amount)
                                shares = loan.circle_member.shares.get()
                                locked_shares = LockedShares.objects.get(loan=loan,shares_transaction__shares=shares)
                                shares_transaction = IntraCircleShareTransaction.objects.create(shares=shares,transaction_type="UNLOCKED",num_of_shares=locked_shares.shares_transaction.num_of_shares,transaction_desc=shares_desc,transaction_code="ST"+uuid.uuid1().hex[:10].upper())
                                created_objects.append(shares_transaction)
                                unlocked_shares = UnlockedShares.objects.create(locked_shares=locked_shares,shares_transaction=shares_transaction)
                                created_objects.append(unlocked_shares)
                                shares_transaction_serializer = SharesTransactionSerializer(shares_transaction)
                                loan_repayment_serializer = LoanRepaymentSerializer(loan_repayment,context={"is_fully_repaid":True})
                                available_shares = circle_instance.get_available_circle_member_shares(circle,user.member)
                                loan_limit = available_shares + settings.LOAN_LIMIT
                                print("loan_limit")
                                print(loan_limit)
                                data = {"status":1,"message":"You have completed your loan.","wallet_transaction":wallet_transaction_serializer.data,"shares_transaction":shares_transaction_serializer.data,"loan_repayment":loan_repayment_serializer.data,'loan_limit':loan_limit}
                                fcm_instance = fcm_utils.Fcm()
                                registration_ids = fcm_instance.get_circle_members_token(circle,user.member)
                                loan.is_fully_repaid = True
                                fcm_data = {"request_type":"UPDATE_AVAILABLE_SHARES","available_shares":available_shares,"circle_acc_number":circle.circle_acc_number,"phone_number":user.member.phone_number}
                                fcm_instance.data_push("multiple",registration_ids,fcm_data)
                                loan.time_of_last_payment = loan_repayment.time_of_repayment
                                loan.save()
                                return Response(data,status=status.HTTP_200_OK)
                            else:
                                ending_balance = latest_loan_amortize.ending_balance - extra_principal
                                print("Loan bado,balance to be amortized")
                                print(ending_balance)
                                amortize_data = loan_instance.amortization_schedule(annual_interest_rate,ending_balance,remaining_number_of_months,latest_loan_amortize.repayment_date)
                                amortize_data['loan'] = loan
                                loan_amortization = LoanAmortizationSchedule(**amortize_data)
                                loan_amortization.save()
                                created_objects.append(loan_amortization)
                                loan_amortization_serializer = LoanAmortizationSerializer(loan_amortization)
                                loan_repayment_serializer = LoanRepaymentSerializer(loan_repayment)
                                available_shares = circle_instance.get_available_circle_member_shares(circle,user.member)
                                loan_limit = available_shares + settings.LOAN_LIMIT
                                total_repayable_amount = loan_amortization.total_repayment * remaining_number_of_months
                                message = "Loan repayment of kes {} has been successfully received.".format(repayment_amount)
                                data = {"status":1,"message":message,"wallet_transaction":wallet_transaction_serializer.data,"loan_repayment":loan_repayment_serializer.data,"loan_limit":loan_limit,"amortization_schedule":loan_amortization_serializer.data,"due_balance":total_repayable_amount,"remaining_num_of_months":remaining_number_of_months}
                                loan.time_of_last_payment = loan_repayment.time_of_repayment
                                loan.save()
                                return Response(data,status=status.HTTP_200_OK)
                        except Exception as e:
                            print(str(e))
                            loan.is_fully_repaid = False
                            loan.save()
                            general_instance = general_utils.General()
                            general_instance.delete_created_objects(created_objects)
                            data ={"status":0,"message":"Unable to complete the loan repayment transaction"}
                            return Response(data,status=status.HTTP_200_OK)
                    data = {"status":0,"message":response}
                    return Response(data,status=status.HTTP_200_OK)
                data = {"status":0,"message":"Unable to complete loan repayment request.The loan is fully repaid."}
                return Response(data,status=status.HTTP_200_OK)
            data = {"status":0,"message":response}
            return Response(data,status=status.HTTP_200_OK)
        data = {"status":0,"message":serializer.errors}
        return Response(data,status=status.HTTP_200_OK)

class LoanGuarantorResponse(APIView):
    """
    Captures guarantor response
    """
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)
    def post(self,request,*args,**kwargs):
        serializer = GuarantorResponseSerializer(data=request.data)
        if serializer.is_valid():
            has_accepted = serializer.validated_data['has_accepted']
            try:
                loan = loanapplication.objects.get(loan_code=serializer.validated_data['loan_code'])
            except loanapplication.DoesNotExist:
                data = {"status":0,"message":"Loan does not exist"}
                return Response(data,status=status.HTTP_200_OK)
            circle,member = loan.circle_member.circle,request.user.member
            try:
                circle_member = CircleMember.objects.get(circle=circle,member=member)
            except CircleMember.DoesNotExist:
                data = {"status":0,"message":"The guarantor is not a member of this circle"}
                return Response(data,status=status.HTTP_200_OK)
            try:
                guarantor = GuarantorRequest.objects.get(circle_member=circle_member,loan=loan)
            except GuarantorRequest.DoesNotExist:
                data = {"status":0,"message":"The guarantor request does not exist"}
                return Response(data,status=status.HTTP_200_OK)
            time_accepted = datetime.datetime.now()
            try:
                if guarantor.has_accepted is None:
                    if has_accepted:
                        created_objects = []
                        loan_instance = loan_utils.Loan()
                        shares = circle_member.shares.get()
                        shares_desc = "Kes {} locked to guarantee loan {} {}".format(guarantor.num_of_shares,member.user.first_name,member.user.last_name)
                        shares_transaction = IntraCircleShareTransaction.objects.create(shares=shares,transaction_type="LOCKED",num_of_shares=guarantor.num_of_shares,transaction_desc=shares_desc,transaction_code="ST"+uuid.uuid1().hex[:10].upper())
                        created_objects.append(shares_transaction)
                        locked_shares = LockedShares.objects.create(shares_transaction=shares_transaction,loan=loan)
                        created_objects.append(locked_shares)
                        guarantor.has_accepted = True
                        guarantor.time_accepted = time_accepted
                        guarantor.save()
                        unguaranteed_amount = loan_instance.get_remaining_guaranteed_amount(loan,loan.circle_member.shares.get())
                        fcm_instance = fcm_utils.Fcm()
                        if unguaranteed_amount == 0:
                            time_processed = datetime.datetime.now()
                            loan_member = loan.circle_member.member
                            wallet_desc = "Credited wallet with loan worth {} {}".format(loan_member.currency,loan.amount)
                            wallet_transaction = Transactions.objects.create(wallet= loan_member.wallet, transaction_type='CREDIT', transaction_time = time_processed,transaction_desc=wallet_desc, transaction_amount= loan.amount, transacted_by = circle.circle_name,transaction_code="WT"+uuid.uuid1().hex[:10].upper())
                            created_objects.append(wallet_transaction)
                            loan.is_approved = True
                            loan.is_disbursed = True
                            loan.time_disbursed = time_processed
                            loan.time_approved = time_processed
                            loan.save()
                            wallet_transaction_serializer = WalletTransactionsSerializer(wallet_transaction)
                            loan_serializer = LoansSerializer(loan)
                            loan_tariff = LoanTariff.objects.get(circle=circle,max_amount__gte=loan.amount,min_amount__lte=loan.amount)
                            annual_interest,date_approved,num_of_months,amount = loan_tariff.monthly_interest_rate * 12,time_processed.date(),loan_tariff.num_of_months,loan.amount
                            loan_amortization = loan_instance.amortization_schedule(annual_interest,amount,num_of_months,date_approved)
                            loan_amortization['loan']=loan
                            loan_amortization_schedule = LoanAmortizationSchedule(**loan_amortization)
                            loan_amortization_schedule.save()
                            created_objects.append(loan_amortization_schedule)
                            remaining_num_of_months,due_balance = num_of_months, loan_amortization_schedule.total_repayment * num_of_months
                            loan_amortization_serializer = LoanAmortizationSerializer(loan_amortization_schedule)
                            registration_id = loan_member.device_token
                            fcm_data = {"request_type":"PROCESS_APPROVED_LOAN","wallet_transaction":wallet_transaction_serializer.data,"loan":loan_serializer.data,"amortization_schedule":loan_amortization_serializer.data,"remaining_num_of_months":remaining_num_of_months,"due_balance":due_balance}
                            fcm_instance.data_push("single",registration_id,fcm_data)
                            title = "Circle %s"%(circle.circle_name)
                            message = "Your loan of %s %s has been successfully processed"%(loan_member.currency,loan.amount)
                            fcm_instance.notification_push("single",registration_id,title,message)
                        loan_limit = circle_utils.Circle().get_available_circle_member_shares(circle,member) + settings.LOAN_LIMIT
                        shares_transaction_serializer = SharesTransactionSerializer(shares_transaction)
                        data = {"status":1,"shares_transaction":shares_transaction_serializer.data,"loan_limit":loan_limit}
                        registration_id = loan.circle_member.member.device_token
                        title = "Circle %s loan guarantor request"%(circle.circle_name)
                        message = "%s %s has accepted to guaranteed you %s %s"%(guarantor.circle_member.member.user.first_name,guarantor.circle_member.member.user.last_name,guarantor.circle_member.member.currency,guarantor.num_of_shares)
                        fcm_instance.notification_push("single",registration_id,title,message)
                        fcm_data = {"request_type":"UPDATE_GUARANTOR_REQUEST_STATUS","loan_code":loan.loan_code,"circle_acc_number":circle.circle_acc_number,"phone_number":member.phone_number,"has_accepted":True}
                        registration_id = loan.circle_member.member.device_token
                        fcm_instance.data_push("single",registration_id,fcm_data)
                    else:
                        guarantor.has_accepted = False
                        guarantor.time_accepted = time_accepted
                        guarantor.save()
                        data = {"status":1}
                        available_shares = circle_utils.Circle().get_guarantor_available_shares(circle,member)
                        fcm_instance = fcm_utils.Fcm()
                        registration_ids = fcm_instance.get_circle_members_token(circle,member)
                        fcm_data = {"request_type":"UPDATE_AVAILABLE_SHARES","circle_acc_number":circle.circle_acc_number,"phone_number":member.phone_number,"available_shares":available_shares}
                        fcm_instance.data_push("multiple",registration_ids,fcm_data)
                        guarantor.save()
                        registration_id = loan.circle_member.member.device_token
                        title = "Circle %s loan guarantor request"%(loan.circle_member.circle.circle_name)
                        message = "%s %s has declined to guarantee you %s %s"%(guarantor.circle_member.member.user.first_name,guarantor.circle_member.member.user.last_name,guarantor.circle_member.member.currency,guarantor.num_of_shares)
                        fcm_instance.notification_push("single",registration_id,title,message)
                        fcm_data = {"request_type":"UPDATE_GUARANTOR_REQUEST_STATUS","loan_code":loan.loan_code,"circle_acc_number":circle.circle_acc_number,"phone_number":member.phone_number,"has_accepted":Fa}
                        registration_id = loan.circle_member.member.device_token
                        fcm_instance.data_push("single",registration_id,fcm_data)
                    return Response(data,status=status.HTTP_200_OK)
                data = {"status":0,"message":"Guarantor loan request has already been processed"}
                return Response(data,status=status.HTTP_200_OK)
            except Exception as exp:
                guarantor.has_accepted = None
                guarantor.time_accepted = None
                guarantor.save()
                general_utils.General().delete_created_objects(created_objects)
                print(str(exp))
                data = {"status":0,"message":"Unable process request."}
                return Response(data,status=status.HTTP_200_OK)
        data = {"status":0,"message":serializer.errors}
        return Response(data,status=status.HTTP_200_OK)

class Loans(APIView):
    """
    lists all loans
    """
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        serializers = CircleAccNoSerializer(data=request.data)
        if serializers.is_valid():
            circle_acc_number = serializers.validated_data['circle_acc_number']
            circle = Circle.objects.get(circle_acc_number=circle_acc_number)
            circle_member = CircleMember.objects.get(circle=circle, member=request.user.member)
            loans = loanapplication.objects.filter(circle_member=circle_member,is_fully_repaid=False)
            if loans.exists():
                loans = LoansSerializer(loans, many=True)
                data = {"status": 1, "loans":loans.data}
                return Response(data, status=status.HTTP_200_OK)
            message = "This user has no loans in this circle"
            data = {"status": 0, "message": message}
            return Response(data,status=status.HTTP_200_OK)
        data = {"status": 0, "message": serializers.errors}
        return Response(data, status=status.HTTP_200_OK)

class LoanGuarantors(APIView):
    """
    Retrieves all guarantors for the loan
    """
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)
    def post(self,request,*args,**kwargs):
        serializer = LoanCodeSerializer(data=request.data)
        if serializer.is_valid():
            loan_code = serializer.validated_data['loan_code']
            loan = loanapplication.objects.get(loan_code=loan_code)
            loan_guarantors = GuarantorRequest.objects.filter(loan=loan)
            loan_guarantors_serializer = LoanGuarantorsSerializer(loan_guarantors,many=True)
            data={"status":1,"loan_guarantors":loan_guarantors_serializer.data}
            return Response(data,status=status.HTTP_200_OK)
        data = {"status":0,"message":serializer.errors}
        return Response(data,status=status.HTTP_200_OK)

class NewLoanGuarantor(APIView):
    """
    Adds new loan guarantor
    """
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)
    def post(self,request,*args,**kwargs):
        serializer = NewLoanGuarantorSerializer(data=request.data)
        if serializer.is_valid():
            loan_code,phone_number,amount = serializer.validated_data['loan_code'],sms_utils.Sms().format_phone_number(serializer.validated_data['phone_number']),serializer.validated_data['amount']
            loan = loanapplication.objects.get(loan_code=loan_code)
            circle = loan.circle_member.circle
            guaranteed_amount = loan.amount - LockedShares.objects.get(loan=loan).shares_transaction.num_of_shares
            fraction_guaranteed = float(amount/guaranteed_amount)
            try:
                loan_guarantor = GuarantorRequest.objects.create(circle_member=CircleMember.objects.get(member=Member.objects.get(phone_number=phone_number),circle=circle),num_of_shares=amount,time_requested=datetime.datetime.today(),fraction_guaranteed=fraction_guaranteed,loan=loan)
                loan_guarantors_serializer = LoanGuarantorsSerializer(loan_guarantor)
                data={"status":1,"loan_guarantor":loan_guarantors_serializer.data}
                circle_instance = circle_utils.Circle()
                actual_shares = circle_instance.get_available_circle_member_shares(circle,loan_guarantor.circle_member.member)
                available_shares = actual_shares - amount
                fcm_instance = fcm_utils.Fcm()
                fcm_data = {"request_type":"UPDATE_AVAILABLE_SHARES","circle_acc_number":circle.circle_acc_number,"phone_number":phone_number,"available_shares":available_shares}
                registration_ids = fcm_instance.get_circle_members_token(circle,loan_guarantor.circle_member.member)
                fcm_instance.data_push("multiple",registration_ids,fcm_data)
                return Response(data,status=status.HTTP_200_OK)
            except Exception as e:
                print(str(e))
                data={"status":0,"message":"The member already exists as your loan guarantor."}
                return Response(data,status=status.HTTP_200_OK)

        data = {"status":0,"message":serializer.errors}
        return Response(data,status=status.HTTP_200_OK)

@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def remove_loan_guarantor(request,*args,**kwargs):
    serializer = CurrentLoanGuarantorSerializer(data=request.data)
    if serializer.is_valid():
        loan = loanapplication.objects.get(loan_code=serializer.validated_data['loan_code'])
        phone_number = sms_utils.Sms().format_phone_number(serializer.validated_data['phone_number'])
        circle_member = CircleMember.objects.get(member=Member.objects.get(phone_number=phone_number),circle=loan.circle_member.circle)
        try:
            loan_guarantor = GuarantorRequest.objects.get(loan=loan,circle_member=circle_member)
        except GuarantorRequest.DoesNotExist:
            data = {"status":0,"message":"Unable to delete guarantor"}
            return Response(data,status=status.HTTP_200_OK)
        if loan_guarantor.has_accepted is None or not loan_guarantor.has_accepted :
            loan_guarantor.delete()
            data = {"status":1}
            circle_instance = circle_utils.Circle()
            available_shares = circle_instance.get_available_circle_member_shares(circle_member.circle,circle_member.member)
            fcm_instance = fcm_utils.Fcm()
            fcm_data = {"request_type":"UPDATE_AVAILABLE_SHARES","circle_acc_number":circle_member.circle.circle_acc_number,"phone_number":circle_member.member.phone_number,"available_shares":available_shares}
            registration_ids = fcm_instance.get_circle_members_token(circle_member.circle,circle_member.member)
            fcm_instance.data_push("multiple",registration_ids,fcm_data)
        else:
            data = {"status":0,"message":"Unable to delete guarantor"}
        return Response(data,status=status.HTTP_200_OK)
    data = {"status":0,"message":serializer.errors}
    return Response(data,status=status.HTTP_200_OK)

class AmortizationSchedule(APIView):
    """
    Retrieves the last amortization schedule
    """
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)
    def post(self,request,*args,**kwargs):
        serializer = LoanCodeSerializer(data=request.data)
        if serializer.is_valid():
            loan_code = serializer.validated_data['loan_code']
            loan = loanapplication.objects.get(loan_code=loan_code)
            if not loan.is_fully_repaid:
                loan_amortization = LoanAmortizationSchedule.objects.filter(loan=loan)
                if loan_amortization.exists():
                    loan_repayment = loan_amortization.filter(~Q(loan_repayment=None)).count()
                    actual_months = LoanTariff.objects.get(max_amount__gte=loan.amount,min_amount__lte=loan.amount,circle=loan.circle_member.circle).num_of_months
                    paid_months = loan_repayment
                    print("paid months")
                    print(paid_months)
                    remaining_number_of_months = actual_months - paid_months
                    latest_amortize_data = loan_amortization.latest('id')
                    total_repayable_amount = latest_amortize_data.total_repayment * remaining_number_of_months
                    loan_amortization_serializer = LoanAmortizationSerializer(latest_amortize_data)
                    data = {"status":1,"amortization_schedule":loan_amortization_serializer.data,"due_balance":total_repayable_amount,"remaining_num_of_months":remaining_number_of_months}
                else:
                    data = {"status":0,"message":"Unable to get the loan's next payment"}
                return Response(data,status=status.HTTP_200_OK)
            else:
                data = {"status":0,"message":"Loan fully repaid can not retrieve next payment."}
                return Response(data,status=status.HTTP_200_OK)
        data = {"status":0,"message":serializer.errors}
        return Response(data,status=status.HTTP_200_OK)

class LoanRepaymentDetails(APIView):
    """
    Retrieves the loan repayment history
    """
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)
    def post(self,request,*args,**kwargs):
        serializer = LoanCodeSerializer(data=request.data)
        if serializer.is_valid():
            loan = loanapplication.objects.get(loan_code=serializer.validated_data['loan_code'])
            if loan.is_approved and loan.is_disbursed:
                loan_repayments = loanrepayment.objects.filter(id__in=loan.loan_amortization.filter().values_list('loan_repayment'))
                if loan_repayments.exists():
                    loan_repayment_serializer = LoanRepaymentSerializer(loan_repayments,many=True)
                    data = {"status":1,"loan_repayment":loan_repayment_serializer.data}
                    return Response(data,status=status.HTTP_200_OK)
                data = {"status":0,"message":"The loan's repayment history does not exist."}
                return Response(data,status=status.HTTP_200_OK)
            data = {"status":0,"message":"Loan not yet approved and disbursed."}
            return Response(data,status=status.HTTP_200_OK)
        data = {"status":0,"message":serializer.errors}
        return Response(data,status=status.HTTP_200_OK)

class UnprocessedLoanGuarantorRequest(APIView):
    """
    Retrieves all unprocessed loan guarantor request
    """
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)
    def post(self,request,*args,**kwargs):
        circle_members = CircleMember.objects.filter(member=request.user.member)
        print circle_members
        unprocessed_requests = GuarantorRequest.objects.filter(has_accepted = None, circle_member__in=circle_members)
        print unprocessed_requests
        unprocessed_requests_serializer = UnprocessedGuarantorRequestSerializer(unprocessed_requests,many=True)
        data = {"status":1,"unprocessed_requests":unprocessed_requests_serializer.data}
        return Response(data,status=status.HTTP_200_OK)
