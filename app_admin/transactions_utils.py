
from member.models import Member
from wallet.models import Wallet, Transactions


class TransactionUtils:
    @staticmethod
    def get_wallet_transaction_by_member(member):
        try:
            wallet = Wallet.objects.get(member=member)
            trx_obj = Transactions.objects.filter(wallet=wallet)
            return trx_obj
        except Exception as exp:
            return None

