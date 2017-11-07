
from member.models import Member
from wallet.models import Wallet, Transactions
from django.db.models import Sum
from django.db.models import Q
from app_utility.sms_utils import Sms


class TransactionUtils:
    @staticmethod
    def get_wallet_transaction_by_member(member):
        try:
            wallet = Wallet.objects.get(member=member)
            trx_obj = Transactions.objects.filter(wallet=wallet).order_by('-transaction_time')
            return trx_obj
        except Exception as exp:
            return None

    @staticmethod
    def search_wallet_transactions(search_val):
        trx = None
        try:
            sms = Sms()
            phone_number = sms.format_phone_number(search_val)
            trx = Transactions.objects.filter(Q(Q(transaction_code=search_val)
                                                | Q(wallet=Wallet.objects.get(member=Member
                                                                              .objects.get(
                                                 Q(Q(phone_number=phone_number)| Q(national_id=search_val))))))).order_by('-transaction_time')
        except Exception as exp:
            trx = Transactions.objects.filter(transaction_code=search_val).order_by('-transaction_time')
            pass
        return trx

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

    @staticmethod
    def get_wallet_trx_by_loan(loan):
        trx = Transactions.objects.filter(transaction_desc__icontains=loan.loan_code, transaction_type__icontains='CREDIT')
        if trx.exists():
            return Transactions.objects.get(transaction_desc__icontains=loan.loan_code, transaction_type='CREDIT',
                                            wallet=Wallet.objects.filter(member=loan.circle_member.member))
        else:
            return None













