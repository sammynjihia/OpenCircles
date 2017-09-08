from rest_framework import serializers
from loan.models import LoanApplication
from circle.models import Circle


class LoanApplicationSerializer(serializers.Serializer):
    loan_amount = serializers.IntegerField()
    pin = serializers.CharField()
    guarantors = serializers.ListField()
    circle_acc_number = serializers.CharField()

    class Meta:
        fields = ["loan_amount", "pin", "guarantors", "circle_acc_number"]

class LoanRepaymentSerializer(serializers.Serializer):
    amount = serializers.IntegerField()
    pin = serializers.CharField()
    circle_acc_number = serializers.CharField()

    class Meta:
        fields = ['amount','pin','circle_acc_number']


class LoansSerializer(serializers.ModelSerializer):
    """
    Serializer for loan listing endpoint
    """

    class Meta:
        model = LoanApplication
        fields = ['circle_member', 'amount', 'interest_rate', 'num_of_repayment_cycles', 'time_of_application', 'is_approved', 'time_approved',
                  'is_disbursed', 'time_disbursed', 'is_fully_repaid', 'time_of_last_repayment']





class CircleAccNoSerializer(serializers.ModelSerializer):
    """
    serializer to retrieve circle account number
    """

    class Meta:
        model = Circle
        fields = ['circle_acc_number']