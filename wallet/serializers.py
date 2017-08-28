from rest_framework import serializers

from .models import Wallet,Transactions

class WallettoWalletTransferSerializer(serializers.Serializer):
    """
    Serializer for wallet tranfer endpoint
    """
    amount = serializers.IntegerField()
    account = serializers.ChoiceField(choices= Wallet.objects.filter().values_list('acc_no',flat=True))
    pin = serializers.IntegerField()

    class Meta():
        fields = ["amount","account","pin"]

class WalletTranferConfirmationSerializer(serializers.Serializer):
    """
    Serializer for wallet transfer confirmation endpoint
    """
    confirmed = serializers.ChoiceField(choices = ["yes","no"])

    class Meta():
        fields=["confirmed"]

class WalletTransactionsSerializer(serializers.ModelSerializer):
    """
    Serializer for  wallet transactions endpoint
    """

    class Meta():
        model = Transactions
        fields = ["transaction_type","transaction_desc","transaction_amount","transacted_by","recipient","transaction_time"]
