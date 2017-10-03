from django.db.models import Sum
from wallet.models import Transactions
import datetime

class Wallet():
    def validate_account_info(self,request,amount,pin,recipient_account):
        sender_wallet = request.user.member.wallet
        if request.user.check_password(pin):
            if sender_wallet.acc_no == recipient_account:
                return False,"Unacceptable transaction.The account number provided is your own"
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
                if balance >= amount:
                    return True,""
                return False,"Insufficient funds in your wallet"
            return False,"Invalid amount"
        return False,"Incorrect pin"

    def deduct_wallet_funds(self,wallet,amount):
        transaction = Transactions.objects.create(wallet=wallet,transaction_type="DEBIT",transaction_time=datetime.datetime.now(),transaction_amount=amount)
        return transaction

    def calculate_wallet_balance(self,wallet):
        credit = Transactions.objects.filter(wallet=wallet,transaction_type="CREDIT").aggregate(total=Sum("transaction_amount"))
        debit = Transactions.objects.filter(wallet=wallet,transaction_type="DEBIT").aggregate(total=Sum("transaction_amount"))
        credit = credit['total'] if credit['total'] is not None else 0
        debit = debit['total'] if debit['total'] is not None else 0
        balance = credit-debit
        return balance
