from django.shortcuts import render

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
from loan.models import LoanApplication as loanapplication,GuarantorRequest

from app_utility import general_utils,fcm_utils,circle_utils

import datetime,json

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
                loan = loanapplication.objects.create(loan_code=loan_code,circle_member=circle_member,amount=loan_amount,interest_rate=circle.annual_interest_rate)
                created_objects.append(loan)
                guarantors = guarantors[0]
                if len(guarantors):
                    try:
                        guarantor_objs = [ GuarantorRequest(loan_application=loan,
                                                            circle_member=CircleMember.objects.get(
                                                                            member=Member.objects.get(phone_number=guarantor["phone_number"]),circle=circle),
                                                            num_of_shares=guarantor["amount"], time_requested=datetime.datetime.today()
                                                            ) for guarantor in guarantors]
                        GuarantorRequest.objects.bulk_create(guarantor_objs)
                        data = {"status":1}
                        return Response(data, status=status.HTTP_200_OK)
                    except Exception as e:
                        print(str(e))
                        instance = general_utils.General()
                        instance.delete_created_objects(created_objects)
                        data = {"status": 0, "message":"Unable to process loan"}
                        return Response(data, status=status.HTTP_200_OK)
                try:
                    shares_desc = "Shares worth {} {} locked to guarantee loan".format(member.currency,loan_amount)
                    shares = circle_member.shares.get()
                    locked_shares = LockedShares.objects.create(shares = shares,num_of_shares=loan_amount, transaction_description=shares_desc)
                    created_objects.append(locked_shares)
                    shares_transaction = IntraCircleShareTransaction.objects.create(shares=shares,transaction_type="LOCKED",num_of_shares=loan_amount,transaction_desc=shares_desc)
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
                    loan_limit = shares_instance.get_available_circle_member_shares(circle,member)
                    available_shares = shares_instance.get_available_circle_member_shares(circle,member)
                    message = "Your loan of {} {} has been successfully processed".format(member.currency,loan_amount)
                    data = {"status":1,"loan":loan_serializer.data,"wallet_transaction":wallet_transaction_serializer.data,"shares_transaction":shares_transaction_serializer.data,"loan_limit":loan_limit,"message":message}
                    instance = fcm_utils.Fcm()
                    param = {"phone":member.phone_number,"available_shares":available_shares}
                    fcm_data = {"request_type":"UPDATE_AVAILABLE_SHARES","params":param}
                    registration_id = instance.get_circle_members_token(circle,member)
                    instance.data_push("multiple",registration_id,fcm_data)
                    return Response(data, status=status.HTTP_200_OK)
                except Exception as e:
                    print(str(e))
                    instance = general_utils.General()
                    instance.delete_created_objects(created_objects)
                    data = {"status": 0, "message":"Unable to process loan"}
                    return Response(data, status=status.HTTP_200_OK)
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
        serializer = LoanRepaymentSerializer(data=request.data)
        if serializer.is_valid():
            pass
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
            loans = loanapplication.objects.filter(circle_member=circle_member)
            if loans.exists():
                loans = LoansSerializer(loans, many=True)
                data = {"status": 1, "loans":loans.data}
                return Response(data, status=status.HTTP_200_OK)
            message = "This user has no loans in this circle"
            data = {"status": 0, "message": message}
            return Response(data,status=status.HTTP_200_OK)
        data = {"status": 0, "message": serializers.errors}
        return Response(data, status=status.HTTP_200_OK)
