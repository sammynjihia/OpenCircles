from rest_framework import serializers
from .models import Shares,LockedShares, IntraCircleShareTransaction, SharesWithdrawalTariff, MgrCircleTransaction
from django.db.models import Sum

class PurchaseSharesSerializer(serializers.Serializer):
    """
    Serializer for purchase shares endpoint
    """
    circle_acc_number = serializers.CharField()
    amount = serializers.IntegerField()
    pin = serializers.CharField()

    class Meta:
        fields = ['circle_acc_number', 'amount', 'pin']

class SharesSerializer(serializers.ModelSerializer):
    """
    Serializer for shares endpoint
    """
    total_shares = serializers.IntegerField(source='num_of_shares')
    locked_shares = serializers.SerializerMethodField()

    class Meta:
        model = Shares
        fields = ['total_shares', 'locked_shares']

    def get_locked_shares(self, share):
        locked_shares = LockedShares.objects.filter(shares=share)
        if locked_shares.exists():
            locked_shares = locked_shares.aggregate(total=Sum('num_of_shares'))
            return int(locked_shares['total'])
        return 0

class MemberSharesSerializer(serializers.Serializer):
    """
    Serializer for member shares endpoint
    """
    circle_acc_number = serializers.CharField()

    class Meta:
        fields = ['circle_acc_number']

class SharesTransactionSerializer(serializers.ModelSerializer):
    """
    Serializer for shares transaction endpoint
    """
    time_of_transaction = serializers.SerializerMethodField()
    type_of_transaction = serializers.CharField(source='transaction_type')
    amount = serializers.IntegerField(source='num_of_shares')
    circle_acc_number = serializers.SerializerMethodField()

    class Meta:
        model = IntraCircleShareTransaction
        fields = ['type_of_transaction', 'amount', 'time_of_transaction',
                  'circle_acc_number', 'transaction_desc']

    def get_time_of_transaction(self, transaction):
        time = transaction.transaction_time.strftime("%Y-%m-%d %H:%M:%S")
        return time

    def get_circle_acc_number(self, transaction):
        return transaction.shares.circle_member.circle.circle_acc_number

class ContributionsTransactionSerializer(serializers.ModelSerializer):
    """
    Serializer for mgr contribution endpoint
    """
    time_of_transaction = serializers.SerializerMethodField()
    type_of_transaction = serializers.CharField(source='transaction_type')
    circle_acc_number = serializers.SerializerMethodField()

    class Meta:
        model = MgrCircleTransaction
        fields = ['type_of_transaction', 'amount', 'time_of_transaction',
                  'circle_acc_number', 'transaction_desc']

    def get_time_of_transaction(self, transaction):
        time = transaction.transaction_time.strftime("%Y-%m-%d %H:%M:%S")
        return time

    def get_circle_acc_number(self, transaction):
        return transaction.circle_member.circle.circle_acc_number

class SharesWithdrawalSerializer(serializers.Serializer):
    """
    serializer for shares withdrawal endpoint
    """
    circle_acc_number = serializers.CharField()
    amount = serializers.IntegerField()
    pin = serializers.CharField()

class SharesTariffSerializer(serializers.ModelSerializer):
    """
    serializer for shares tariff
    """
    charges = serializers.IntegerField(source='amount')
    class Meta:
        model = SharesWithdrawalTariff
        fields = ['min_amount', 'max_amount', 'charges']

    """
    Serializer for circle member shares
    """
    circle_acc_number = serializers.CharField()
    phone_number = serializers.CharField()

class ContributionCircleAccSerializer(serializers.Serializer):
    """
    Serializer for contribution Disbursal endpoint
    """
    circle_acc_number = serializers.CharField()