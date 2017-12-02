from django.db.models import Sum
from wallet.models import Transactions, PendingMpesaTransactions
import datetime

class Wallet():
    def validate_account_info(self,request,amount,pin,recipient_account):
        sender_wallet = request.user.member.wallet
        if request.user.check_password(pin):
            if sender_wallet.acc_no == recipient_account:
                return False,"Unacceptable transaction.The phone number provided is your own"
            balance = self.calculate_wallet_balance(sender_wallet)
            if balance >= amount:
                return True,""
            return False,"Insufficient funds in your wallet"
        return False,"Incorrect pin"

    def validate_account(self,request,pin,amount):
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
        pending_total = PendingMpesaTransactions.objects.filter(is_valid=True, member=member).aggregate(total=Sum('amount'))
        return pending_total['total'] if pending_total['total'] is not None else 0

    def calculate_wallet_balance(self,wallet):
        credit = Transactions.objects.filter(wallet=wallet,transaction_type="CREDIT").aggregate(total=Sum("transaction_amount"))
        debit = Transactions.objects.filter(wallet=wallet,transaction_type="DEBIT").aggregate(total=Sum("transaction_amount"))
        credit = credit['total'] if credit['total'] is not None else 0
        debit = debit['total'] if debit['total'] is not None else 0
        print("debit")
        print(debit)
        print("credit")
        print(credit)
        balance = credit-debit
        balance = round(balance,4)
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
