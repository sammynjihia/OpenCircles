import datetime
import json
from member.models import Member
from wallet.models import Wallet, Transactions, AdminMpesaTransaction_logs
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
    def get_days_wallet_transactions():
        trx = Transactions.objects.filter(transaction_time__range=(
                datetime.datetime.combine(datetime.datetime.today(), datetime.time.min),
                datetime.datetime.combine(datetime.datetime.today(), datetime.time.max))).order_by('-transaction_time')
        return trx

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
    def get_transaction_by_transaction_code(transaction_code):
        try:
            Transactions.objects.get(transaction_code=transaction_code)
        except:
            return None


    @staticmethod
    def get_wallet_balance_wallet_id(id):
        wallet = Wallet.objects.get(id=id)
        trx_credit = Transactions.objects.filter(wallet=wallet, transaction_type__icontains='CREDIT')\
            .aggregate(total=Sum('transaction_amount'))['total']
        trx_credit = trx_credit if trx_credit is not None else 0
        trx_debit = Transactions.objects.filter(wallet=wallet, transaction_type__icontains='DEBIT')\
            .aggregate(total=Sum('transaction_amount'))['total']
        trx_debit = trx_debit if trx_debit is not None else 0
        return trx_credit - trx_debit

    @staticmethod
    def get_wallet_trx_by_loan(loan):
        trx = Transactions.objects.filter(transaction_desc__icontains=loan.loan_code, transaction_type__icontains='CREDIT')
        if trx.exists():
            return Transactions.objects.get(transaction_desc__icontains=loan.loan_code, transaction_type='CREDIT',
                                            wallet=Wallet.objects.filter(member=loan.circle_member.member))
        else:
            return None

    @staticmethod
    def get_mpesa_transactions_log():
        return AdminMpesaTransaction_logs.objects.all().order_by('-transaction_time')

    @staticmethod
    def search_for_mpesa_transaction(transaction_code=None, start_date=None, end_date=None):

        if transaction_code is not None and start_date is None and end_date is None:
            return AdminMpesaTransaction_logs.objects.filter(TransactioID=transaction_code).order_by('-transaction_time')

        if transaction_code is None and start_date is not None and end_date is None:
            return AdminMpesaTransaction_logs.objects.filter(transaction_time__gte=start_date)\
                .order_by('-transaction_time')

        if transaction_code is None and start_date is None and end_date is not None:
            return AdminMpesaTransaction_logs.objects.filter(transaction_time__lte=datetime.datetime
                                                             .combine(end_date, datetime.time.max))\
                .order_by('-transaction_time')


        if transaction_code is not None and start_date is not None and end_date is not None:
            return AdminMpesaTransaction_logs.objects.filter(TransactioID=transaction_code,
                                                             transaction_time__range=(datetime.datetime.combine(start_date, datetime.time.min),
                datetime.datetime.combine(end_date, datetime.time.max))) \
                .order_by('-transaction_time')

        if transaction_code is None and start_date is not None and end_date is not None:
            return AdminMpesaTransaction_logs.objects.filter(transaction_time__range=(datetime.datetime.combine(start_date, datetime.time.min),
                datetime.datetime.combine(end_date, datetime.time.max))) \
                .order_by('-transaction_time')

    @staticmethod
    def get_mpesa_transaction_by_transaction_code(transaction_code):
        transaction_obj = AdminMpesaTransaction_logs.objects.get(TransactioID=transaction_code.strip())
        amount = 0
        try:
            res_json = json.loads(transaction_obj.Response.strip())
            if transaction_obj.TransactionType.strip() == 'C2B':
                amount = res_json['TransAmount']
            elif transaction_obj.TransactionType.strip() == 'B2C':
                res_params = res_json['Result']['ResultParameters']['ResultParameter']
                for param in res_params:
                    if param['Key'] == 'TransactionAmount':
                        amount = param['Value']
                        break
        except Exception as e:
            print(str(e))
            pass

        mpesa_trasaction = {
            'transaction_code': transaction_obj.TransactioID,
            'is_committed': transaction_obj.is_committed,
            'type': transaction_obj.TransactionType,
            'time': transaction_obj.transaction_time,
            'amount': amount,
            'response': transaction_obj.Response
        }
        return mpesa_trasaction











