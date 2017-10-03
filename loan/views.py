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
from rest_framework.decorators import api_view
from rest_framework.reverse import reverse

from circle.models import Circle,CircleMember
from member.models import Member
from shares.models import LockedShares,IntraCircleShareTransaction
from wallet.models import Transactions
from loan.models import LoanApplication as loanapplication,GuarantorRequest,LoanAmortizationSchedule,LoanRepayment as loanrepayment,LoanGuarantor

from app_utility import general_utils,fcm_utils,circle_utils,wallet_utils,loan_utils

import datetime,json,math

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
                                GuarantorRequest.objects.bulk_create(guarantor_objs)
                                locked_shares = LockedShares.objects.create(shares = shares,num_of_shares=available_shares, transaction_description=shares_desc)
                                created_objects.append(locked_shares)
                                shares_transaction = IntraCircleShareTransaction.objects.create(shares=shares,transaction_type="LOCKED",num_of_shares=available_shares,transaction_desc=shares_desc,locked_loan=loan)
                                created_objects.append(shares_transaction)
                                available_shares = circle_instance.get_available_circle_member_shares(circle,member)
                                print(available_shares)
                                loan_limit = available_shares+settings.LOAN_LIMIT
                                print(loan_limit)
                                shares_transaction_serializer = SharesTransactionSerializer(shares_transaction)
                                print(shares_transaction_serializer.data)
                                loan_serializer = LoansSerializer(loan)
                                data = {"status":1,"shares_transaction":shares_transaction_serializer.data,"message":"Loan application successfully received.Waiting for guarantors approval","loan":loan_serializer.data,"loan_limit":loan_limit}
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
                        data = {"status":0,"message":"Loan can not be processed.Guarantors needed"}
                        return Response(data,status=status.HTTP_200_OK)
                    try:
                        locked_shares = LockedShares.objects.create(shares=shares,num_of_shares=loan_amount, transaction_description=shares_desc)
                        created_objects.append(locked_shares)
                        shares_transaction = IntraCircleShareTransaction.objects.create(shares=shares,transaction_type="LOCKED",num_of_shares=loan_amount,transaction_desc=shares_desc,locked_loan=loan)
                        created_objects.append(shares_transaction)
                        wallet_desc = "Credited wallet with loan worth {} {}".format(member.currency,loan_amount)
                        wallet_transaction = Transactions.objects.create(wallet= member.wallet, transaction_type='CREDIT', transaction_time = datetime.datetime.now(),transaction_desc=wallet_desc, transaction_amount= loan_amount, transacted_by = circle.circle_name)
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
        print(request.data)
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
                        data = {"status":0,"message":"Unable to repay loan.The loan has not been amortized.Kindly contact admin for further details"}
                        return Response(data,status=status.HTTP_200_OK)
                    latest_loan_amortize = loan_amortize.latest('id')
                    valid,response = loan_instance.validate_repayment_amount(repayment_amount,latest_loan_amortize)
                    if valid:
                        circle = loan.circle_member.circle
                        loan_tariff = LoanTariff.objects.get(circle=circle,max_amount__gte=loan.amount,min_amount__lte=loan.amount)
                        remaining_number_of_months = loan_tariff.num_of_months-loan_amortize.count()
                        annual_interest_rate = loan_tariff.monthly_interest_rate*12
                        if repayment_amount > latest_loan_amortize.total_repayment and remaining_number_of_months == 0:
                            data = {"status":0,"message":"The amount entered exceeds this month's loan repayment amount."}
                            return Response(data,status=status.HTTP_200_OK)
                        try:
                            wallet_desc = "Kes {} sent to circle {} for loan repayment".format(repayment_amount,circle.circle_name)
                            wallet_transaction = Transactions.objects.create(wallet = user.member.wallet,transaction_type="DEBIT",transaction_desc=wallet_desc,recipient=circle.circle_acc_number,transaction_amount=repayment_amount,transaction_time=datetime.datetime.now())
                            created_objects.append(wallet_transaction)
                            loan_repayment = loanrepayment.objects.create(amount=repayment_amount,time_of_repayment=datetime.datetime.now(),loan=loan,amortization_schedule=latest_loan_amortize)
                            created_objects.append(loan_repayment)
                            guarantors = LoanGuarantor.objects.filter(circle_member=loan.circle_member)
                            extra_principal = repayment_amount - latest_loan_amortize.total_repayment
                            ending_balance = math.ceil(latest_loan_amortize.ending_balance) - extra_principal
                            if guarantors.exists():
                                #if any guarantors exist unlock there shares according to the fraction of money they have guaranteed
                                pass
                            wallet_transaction_serializer = WalletTransactionsSerializer(wallet_transaction)
                            circle_instance = circle_utils.Circle()
                            if remaining_number_of_months == 0 or ending_balance == 0:
                                shares_desc = "Shares worth {} {} unlocked".format(user.member.currency,loan.amount)
                                shares = loan.circle_member.shares.get()
                                locked_shares = IntraCircleShareTransaction.objects.get(locked_loan=loan)
                                shares_transaction = IntraCircleShareTransaction.objects.create(shares=shares,transaction_type="UNLOCKED",num_of_shares=locked_shares.num_of_shares,transaction_desc=shares_desc,locked_loan=loan)
                                created_objects.append(shares_transaction)
                                shares_transaction_serializer = SharesTransactionSerializer(shares_transaction)
                                loan_repayment_serializer = LoanRepaymentSerializer(loan_repayment,context={"is_fully_repaid":True})
                                available_shares = circle_instance.get_available_circle_member_shares(circle,user.member)
                                loan_limit = available_shares + settings.LOAN_LIMIT
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
                data = {"status":0,"message":"Unable to complete the loan repayment transaction.The loan is already fully repaid."}
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
            try:
                has_accepted = serializer.validated_data['has_accepted']
                loan = LoanApplication.objects.get(loan_code=serializer.validated_data['loan_code'])
                circle,member = loan.circle_member.circle,request.user.member
                circle_member = CircleMember.objects.get(circle=circle,member=member)
                guarantor = GuarantorRequest.objects.get(circle_member=circle_member,loan=loan)
                if has_accepted:
                    time_accepted = datetime.datetime.now()
                    created_objects = []
                    shares = circle_member.shares.get()
                    shares_desc = "Kes {} locked to guarantee loan {} {}".format(guarantor.num_of_shares,member.user.first_name,member.user.last_name)
                    locked_shares = LockedShares.objects.create(shares=shares,num_of_shares=guarantor.num_of_shares,transaction_description=shares_desc)
                    created_objects.append(locked_shares)
                    shares_transaction = IntraCircleShareTransaction.objects.create(shares=shares,transaction_type="LOCKED",num_of_shares=guarantor.num_of_shares,transaction_desc=shares_desc,locked_loan=loan)
                    created_objects.append(shares_transaction)
                    guarantor.has_accepted = True
                    guarantor.time_accepted = time_accepted
                    shares_transaction_serializer = SharesTransactionSerializer(shares_transaction)
                    data = {"status":1,"shares_transaction":shares_transaction_serializer.data}
                else:
                    guarantor.has_accepted = False
                    guarantor.time_accepted = time_accepted
                    data = {"status":1,"shares_transaction":{}}
                guarantor.save()
                available_shares = circle_utils.Circle().get_available_circle_member_shares(circle,member)
                fcm_instance = fcm_utils.Fcm()
                registration_ids = fcm_instance.get_circle_members_token(circle,member)
                fcm_data = {"request_type":"UPDATE_AVAILABLE_SHARES","circle_acc_number":circle.circle_acc_number,"phone_number":member.phone_number,"available_shares":available_shares}
                fcm_instance.data_push("multiple",registration_ids,fcm_data)
                return Response(data,status=status.HTTP_200_OK)
            except Exception as exp:
                print(str(exp))
                data = {"status":0,"message":"Unable process response."}
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
