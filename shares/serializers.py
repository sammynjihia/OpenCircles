from rest_framework import serializers

from .models import Shares,LockedShares

from django.db.models import Sum

class PurchaseSharesSerializer(serializers.Serializer):
    """
    Serializer for purchase shares endpoint
    """
    circle_acc_number = serializers.CharField()
    amount = serializers.IntegerField()
    pin = serializers.CharField()

    class Meta():
        fields = ['circle_acc_number','amount','pin']

class SharesSerializer(serializers.ModelSerializer):
    """
    Serializer for shares endpoint
    """
    total_shares = serializers.FloatField(source='num_of_shares')
    locked_shares = serializers.SerializerMethodField()

    class Meta():
        model = Shares
        fields = ['total_shares','locked_shares']

    def get_locked_shares(self,share):
        locked_shares = LockedShares.objects.filter(shares=share)
        if locked_shares.exists():
            locked_shares = locked_shares.aggregate(total=Sum('num_of_shares'))
            return float(locked_shares['total'])
        return 0.0

class MemberSharesSerializer(serializers.Serializer):
    """
    Serializer for member shares endpoint
    """
    circle_acc_number = serializers.CharField()
    token = serializers.CharField()

    class Meta():
        fields = ['circle_acc_number','token']
