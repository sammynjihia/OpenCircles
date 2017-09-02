from django.shortcuts import render
from loan.models import LoanApplication as loanapplication,GuarantorRequest
from loan.serializers import LoanApplicationSerializer

from rest_framework.views import APIView
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.reverse import reverse



from circle.models import Circle,CircleMember
from member.models import Member
from shares.models import LockedShares
from wallet.models import Transactions
import datetime
import json




# Create your views here.

@api_view(['GET'])
def api_root(request,format=None):
    return Response({
                        "loan_application":reverse('loan_application',request=request,format=format)

    })


class LoanApplication(APIView):
    authentication_classes = (TokenAuthentication, )
    permission_classes = (IsAuthenticated, )

    def post(self, request, *args, **kwargs):
        print request.data
        if 'guarantors' in request.data:
            mutable = request.data._mutable
            request.data._mutable = True
            request.data['guarantors'] = json.loads(request.data['guarantors'])
            request.data._mutable = mutable
        serializers = LoanApplicationSerializer(data=request.data)

        if serializers.is_valid():
            pin = serializers.validated_data["pin"]
            loan_amount = serializers.validated_data["loan_amount"]
            guarantors = serializers.validated_data["guarantors"]
            circle = Circle.objects.get(circle_acc_number=serializers.validated_data["circle_acc_number"])

            if request.user.check_password(pin):
                circle_member = CircleMember.objects.get(circle=circle,member=request.user.member)
                loan = loanapplication.objects.create(circle_member=circle_member,amount=loan_amount,interest_rate=circle.annual_interest_rate)
                guarantors = guarantors[0]
                if len(guarantors):
                    try:
                        guarantor_objs = [ GuarantorRequest(loan_application=loan,
                                                            circle_member=CircleMember.objects.get(
                                                                            member=Member.objects.get(phone_number=guarantor['phone_number']),circle=circle),
                                                            num_of_shares=guarantor["amount"], time_requested=datetime.datetime.today()
                                                            ) for guarantor in guarantors]
                        GuarantorRequest.objects.bulk_create(guarantor_objs)
    #                   /*disperse message to guarantors*/
                        data = {"status":1}
                        return Response(data, status=status.HTTP_200_OK)
                    except Exception as e:
                        print(str(e))
                        data = {"status": 0, "message":"unable to process loan"}
                        return Response(data, status=status.HTTP_200_OK)

                locked_shares = LockedShares.objects.create(shares = circle_member.shares.get(),num_of_shares=loan_amount, transaction_description="Shares locked to guarantee loan",
                                                            extra_info="")
                transaction = Transactions.objects.create(wallet= request.user.member.wallet, transaction_type='CREDIT', transaction_time = datetime.datetime.now(),
                                                          transaction_desc="Added funds to wallet", transaction_amount= loan_amount, transacted_by = circle.circle_name)
                loan._do_update(is_approved=True, is_disbursed=True, time_disbursed=datetime.datetime.now(), time_approved=datetime.datetime.now())

                data = {"status":1}
                return Response(data, status=status.HTTP_200_OK)
