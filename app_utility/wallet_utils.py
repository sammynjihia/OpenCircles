from django.db.models import Sum
from wallet.models import Transactions, PendingMpesaTransactions, AirtimePurchaseLog, B2BTransaction_log
from django.db.models import Q
import datetime

class Wallet():
    def validate_account_info(self, request, amount, pin, recipient_account):
        sender_wallet = request.user.member.wallet
        if request.user.check_password(pin):
            if recipient_account is not None:
                if sender_wallet.acc_no == recipient_account:
                    return False,"Unacceptable transaction.The phone number provided is your own"
            balance = self.calculate_wallet_balance(sender_wallet)
            balance -= float(self.get_pending_mpesa_amount(request.user.member))
            if balance >= amount:
                return True,""
            return False,"Insufficient funds in your wallet"
        return False,"Incorrect pin"

    def validate_account(self, request, pin, amount):
        if request.user.check_password(pin):
            if amount > 0:
                wallet = request.user.member.wallet
                balance = self.calculate_wallet_balance(wallet)
                balance -= float(self.get_pending_mpesa_amount(request.user.member))
                print("wallet balance")
                print(balance)
                if balance >= amount:
                    return True,""
                return False,"Insufficient funds in your wallet"
            return False,"Invalid amount"
        return False,"Incorrect pin"

    def get_pending_mpesa_amount(self, member):
        pending_trans = PendingMpesaTransactions.objects.filter(is_valid=True, member=member).aggregate(total_pending=Sum('amount')+Sum('charges'))
        pending_total = pending_trans['total_pending'] if pending_trans['total_pending'] is not None else 0
        return pending_total

    def calculate_wallet_balance(self,wallet):
        credit = Transactions.objects.filter(wallet=wallet,transaction_type="CREDIT").aggregate(total=Sum("transaction_amount"))
        debit = Transactions.objects.filter(wallet=wallet,transaction_type="DEBIT").aggregate(total=Sum("transaction_amount"))
        credit = credit['total'] if credit['total'] is not None else 0
        debit = debit['total'] if debit['total'] is not None else 0
        print("debit")
        print(debit)
        print("credit")
        print(credit)
        balance = float(credit-debit)
        balance_str = str(balance).split('.')
        whole, dec = balance_str[0], balance_str[1]
        if len(dec) > 4:
            dec = dec[0:4]
            new_amount = whole + "." + dec
            balance = float(new_amount)
        return balance

    def save_transaction_code(self,transaction):
        code = "WT{}".format(transaction.wallet.member.national_id)
        trans = Transactions.objects.filter(transaction_code__startswith = code)
        if trans.exists():
            latest_transaction = trans.latest('id')
            value = int(latest_transaction.transaction_code[len(code):])
            new_value = value + 1
            new_value = str(new_value)
            value = new_value if len(new_value)>1 else new_value.zfill(2)
            transaction.transaction_code = code + value
        else:
            transaction.transaction_code = code + "01"
        transaction.save()
        return transaction

    def update_airtime_trx(self):
        a_t = AirtimePurchaseLog.objects.all()
        for t in a_t:
            t.is_committed = t.is_purchased
            print(t.is_committed)
            t.save()

    def update_pending_trx(self):
        bank_paybills = ["880100", "400200", "247247", "222111", "5225222"]
        b2b_trxs = B2BTransaction_log.objects.filter(~Q(Recipient_PayBillNumber="564433"))
        airtime_trx_ids = b2b_trxs.filter(Recipient_PayBillNumber="525900").values_list('OriginatorConversationID')
        PendingMpesaTransactions.objects.filter(originator_conversation_id__in=airtime_trx_ids).update(type='B2B', purpose="buy airtime")
        bank_trx_ids = b2b_trxs.filter(Recipient_PayBillNumber__in=bank_paybills).values_list('OriginatorConversationID')
        PendingMpesaTransactions.objects.filter(originator_conversation_id__in=bank_trx_ids).update(type='B2B', purpose="bank")
        paybill_trx_ids = b2b_trxs.filter(~Q(OriginatorConversationID__in=airtime_trx_ids|bank_trx_ids)).values_list('OriginatorConversationID')
        PendingMpesaTransactions.objects.filter(originator_conversation_id__in=paybill_trx_ids).update(type='B2B', purpose="paybill")
