
from member.models import Member
from wallet.models import Wallet, Transactions
from django.db.models import Sum


class TransactionUtils:
    @staticmethod
    def get_wallet_transaction_by_member(member):
        try:
            wallet = Wallet.objects.get(member=member)
            trx_obj = Transactions.objects.filter(wallet=wallet)
            return trx_obj
        except Exception as exp:
            return None

    @staticmethod
    def search_wallet_transactions(search_val):
        return Transactions.objects.filter(transaction_code=search_val)

    @staticmethod
    def get_transaction_by_id(id):
        return Transactions.objects.get(id=id)

    @staticmethod
    def get_wallet_balance_wallet_id(id):
        wallet = Wallet.objects.get(id=id)
        trx_credit = Transactions.objects.filter(wallet=wallet, transaction_type__icontains='CREDIT')\
            .aggregate(total=Sum('transaction_amount'))['total']
        trx_debit = Transactions.objects.filter(wallet=wallet, transaction_type__icontains='DEBIT')\
            .aggregate(total=Sum('transaction_amount'))['total']
        return trx_credit - trx_debit











