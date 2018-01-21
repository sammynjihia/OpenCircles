from rest_framework import serializers

from .models import Wallet,Transactions

import datetime

class WallettoWalletTransferSerializer(serializers.Serializer):
    """
    Serializer for wallet tranfer endpoint
    """
    amount = serializers.IntegerField()
    phone_number = serializers.CharField()
    pin = serializers.IntegerField()

    class Meta():
        fields = ["amount", "phone_number", "pin"]

class WalletTransactionsSerializer(serializers.ModelSerializer):
    """
    Serializer for  wallet transactions endpoint
    """
    transaction_time = serializers.SerializerMethodField()

    class Meta():
        model = Transactions
        fields = ["transaction_type", "transaction_desc", "transaction_amount", "transacted_by",
                  "recipient", "transaction_time"]

    def get_transaction_time(self, transaction):
        return transaction.transaction_time.strftime("%Y-%m-%d %H:%M:%S")

class WalletTransactionSerializer(serializers.Serializer):
    """
    Serializer for specific wallet transaction endpoint
    """
    transaction_id = serializers.IntegerField()

class MpesaToWalletSerializer(serializers.Serializer):
    """
    Serializer for M-pesa to wallet transaction endpoint
    """
    amount = serializers.IntegerField()

    class Meta():
        fields = ["amount"]


class WalletToMpesaSerializer(serializers.Serializer):
    """
    Serializer for Wallet to Mpesa (B2C) transaction endpoint
    """

    amount = serializers.IntegerField()
    phone_number = serializers.CharField()
    pin = serializers.CharField()

    class Meta():
        fields = ["amount", "phone_number", "pin"]

class WalletToPayBillSerializer(serializers.Serializer):
    """
    Serializer for Wallet to Mpesa (B2B) transaction endpoint
    """

    amount = serializers.IntegerField()
    business_number = serializers.CharField()
    account_number = serializers.CharField()
    pin = serializers.CharField()

    class Meta():
        fields = ["amount", "business_number", "account_number", "pin"]

class BrainTreeTransactionSerializer(serializers.Serializer):
    """
    serializer for brain tree transaction endpoint
    """
    nonce = serializers.CharField()
    amount = serializers.IntegerField()


class WalletToBankSerializer(serializers.Serializer):
    """
    serializer for Waalet to Bank's paybill number (B2B) transaction endpoint
    """
    amount = serializers.IntegerField()
    pin = serializers.CharField()
    bank_name = serializers.CharField()
    paybill_number = serializers.CharField()
    account_number = serializers.CharField()

    class Meta():
        fields = ["amount", "pin", "bank_name", "paybill_number", "account_number"]
