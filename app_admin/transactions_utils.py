import datetime
import json
from member.models import Member
from wallet.models import Wallet, Transactions, AdminMpesaTransaction_logs, B2CTransaction_log
from wallet.serializers import WalletTransactionsSerializer
from django.db.models import Sum
from django.db.models import Q
from app_utility.sms_utils import Sms
from app_utility.wallet_utils import Wallet as WalletUtils
from app_utility import fcm_utils


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
            return  Transactions.objects.get(transaction_code=transaction_code)
        except Exception as e:
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
            elif transaction_obj.TransactionType.strip() == 'B2C' or transaction_obj.TransactionType.strip() == 'B2B':
                res_params = res_json['Result']['ResultParameters']['ResultParameter']
                for param in res_params:
                    if param['Key'] == 'TransactionAmount':
                        amount = param['Value']
                        break
                    if param['Key'] == 'Amount':
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
            'response': transaction_obj.Response.strip()
        }
        return mpesa_trasaction

    @staticmethod
    def do_mpesa_wallet_reconciliation_reconciliation(mpesa_transaction):
        if mpesa_transaction['type'] == 'C2B':
            return TransactionUtils.commit_mpesa_c2b_transaction(mpesa_transaction)
        elif mpesa_transaction['type'] == 'B2C':
            return TransactionUtils.commit_mpesa_b2c_transaction(mpesa_transaction)

    @staticmethod
    def commit_mpesa_c2b_transaction(mpesa_transaction):
        trx_code = mpesa_transaction['transaction_code']
        amount = mpesa_transaction['amount']
        trx_time = mpesa_transaction['time']

        response_json = json.loads(mpesa_transaction['response'])
        bill_ref_number = response_json['BillRefNumber']
        msisdn = response_json['MSISDN']
        c2b_first_name = response_json['FirstName']
        c2b_middle_name = response_json['MiddleName']

        sms = Sms()
        member_phone_number = sms.format_phone_number(bill_ref_number)
        mpesa_trx_obj = AdminMpesaTransaction_logs.objects.get(TransactioID=trx_code.strip())
        if Member.objects.filter(phone_number=member_phone_number).exists() and mpesa_trx_obj.is_committed is False:
            member = Member.objects.get(phone_number=member_phone_number)
            wallet = Wallet.objects.get(member=member)
            try:
                wallet_utils = WalletUtils()
                new_balance = wallet_utils.calculate_wallet_balance() + amount
                trx_obj = Transactions()
                trx_obj.transaction_type = 'CREDIT'
                trx_obj.transaction_time = trx_time
                trx_obj.transaction_desc = """
                    {} confirmed. You have received KES {} from {} {} {} via M-PESA at {}. New wallet balance is KES {}
                """.format(trx_code, amount, msisdn, c2b_first_name, c2b_middle_name,
                           trx_time.strftime('%Y-%m-%d %H-%M-%s'), new_balance ).strip()
                trx_obj.transaction_amount = amount
                trx_obj.transacted_by = '{} {} {}'.format(msisdn, c2b_first_name, c2b_middle_name)
                trx_obj.recipient = 'SELF'
                trx_obj.transaction_code = trx_code
                trx_obj.wallet = wallet
                trx_obj.source = 'MPESA C2B'
                trx_obj.save()
                mpesa_trx_obj.is_committed = True
                mpesa_trx_obj.save()

                serializer = WalletTransactionsSerializer(trx_obj)
                instance = fcm_utils.Fcm()
                registration_id = member.device_token
                fcm_data = {"request_type": "MPESA_TO_WALLET_TRANSACTION",
                            "transaction": serializer.data}
                instance.data_push("single", registration_id, fcm_data)
                return True
            except Exception as e:
                return False
        else:
            return False

    @staticmethod
    def commit_mpesa_b2c_transaction(mpesa_transaction):
        trx_code = mpesa_transaction['transaction_code']
        amount = mpesa_transaction['amount']
        trx_time = mpesa_transaction['time']

        response_json = json.loads(mpesa_transaction['response'])
        originator_conversation_id = response_json['Result']['OriginatorConversationID']
        result_code = int(response_json['Result']['ResultCode'])

        b2c_log = B2CTransaction_log.objects.get(OriginatorConversationID=originator_conversation_id)
        member_phone_number = b2c_log.Recipient_PhoneNumber

        mpesa_trx_obj = AdminMpesaTransaction_logs.objects.get(TransactioID=trx_code.strip())
        if Member.objects.filter(phone_number=member_phone_number).exists() \
                and mpesa_trx_obj.is_committed is False and result_code == 0:
            member = Member.objects.get(phone_number=member_phone_number)
            wallet = Wallet.objects.get(member=member)

            # Get M-PESA recipient
            result_params = response_json['Result']['ResultParameters']['ResultParameter']
            recipient = ''
            for result_param_obj in result_params:
                if result_param_obj['Key'] == 'ReceiverPartyPublicName':
                    recipient = result_param_obj['Value']

            # Get transaction charges
            charges = 0
            if amount >= 100 and amount <= 1000:
                charges = 16
            elif amount >= 1001 and amount <= 70000:
                charges = 23

            try:
                wallet_utils = WalletUtils()
                new_balance = wallet_utils.calculate_wallet_balance() - (amount + charges)

                # Save transactions Objects
                trx_obj = Transactions()
                trx_obj.transaction_type = 'DEBIT'
                trx_obj.transaction_time = trx_time
                trx_obj.transaction_desc = """
                    {} confirmed. You have sent KES {} to {} via M-PESA at {}.
                    Transaction cost is KES {}. New wallet balance is KES {}
                """.format(trx_code, amount, recipient, trx_time.strftime('%Y-%m-%d %H-%M-%s'), charges, new_balance).strip()
                trx_obj.transaction_amount = amount+charges
                trx_obj.transacted_by = 'SELF'
                trx_obj.recipient = recipient
                trx_obj.transaction_code = trx_code
                trx_obj.wallet = wallet
                trx_obj.source = 'MPESA B2C'
                trx_obj.save()

                # Update mpesa log
                mpesa_trx_obj.is_committed = True
                mpesa_trx_obj.save()

                # Send FCM message
                serializer = WalletTransactionsSerializer(trx_obj)
                instance = fcm_utils.Fcm()
                registration_id = member.device_token
                fcm_data = {"request_type": "MPESA_TO_WALLET_TRANSACTION",
                            "transaction": serializer.data}
                instance.data_push("single", registration_id, fcm_data)
                return True
            except Exception as e:
                return False
        else:
            return False

    @staticmethod
    def get_transactions_by_day_and_source(search_date=None, source=None):

        if search_date is None:
            search_date = datetime.datetime.today()

        source = source if source is not None else 'MPESA C2B'

        trx_objs = Transactions.objects.filter(transaction_time__range=(
            datetime.datetime.combine(search_date, datetime.time.min),
            datetime.datetime.combine(search_date, datetime.time.max)), source__icontains=source)\
            .order_by('-transaction_time')
        total = trx_objs.aggregate(total=Sum('transaction_amount'))
        print(trx_objs)
        if trx_objs.__len__() is not 0:
            trx_hr_summation = []
            current_hr = trx_objs.first().transaction_time.hour
            for obj in trx_objs:

                if obj.transaction_time.hour is not current_hr or obj is trx_objs.first():
                    current_hr = obj.transaction_time.hour
                    hourly_obj = trx_objs.filter(transaction_time__hour=current_hr)\
                        .aggregate(total=Sum('transaction_amount'))
                    trx_hr_summation.append({
                        'hour': current_hr,
                        'amount': hourly_obj['total'] if hourly_obj['total'] is not None else 0
                    })
                else:
                    continue

            return {
                'hourly_grouping': trx_hr_summation,
                'hourly_grouping_json': json.dumps(trx_hr_summation),
                'transactions': trx_objs,
                'total_amount': total['total'] if total['total'] is not None else 0,
                'count_of_transactions': trx_objs.count(),
                'max_amount': '',
                'min_amount': '',
                'avg_amount': '',
                'date': search_date,
                'trx_type': source
            }
        else:
            return None













