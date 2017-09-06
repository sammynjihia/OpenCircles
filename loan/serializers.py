from rest_framework import serializers

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
