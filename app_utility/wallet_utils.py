from wallet.models import Transactions
import datetime

class Wallet():
    def validate_account_info(self,request,amount,pin,recipient_account):
        sender_wallet = request.user.member.wallet
        print type(pin)
        print request.user
        print request.user.check_password(pin)
        if request.user.check_password(pin):
            if sender_wallet.acc_no == recipient_account:
                return False,"Unacceptable transaction.The account number provided is your own"
            return True,""
        return False,"Incorrect pin"

    def validate_account(self,request,pin,amount):
        if request.user.check_password(pin):
            wallet = request.user.member.wallet
            transaction = self.deduct_wallet_funds(wallet,amount)
            return True,transaction
        return False,"Incorrect pin"

    def deduct_wallet_funds(self,wallet,amount):
        transaction = Transactions.objects.create(wallet=wallet,transaction_type="DEBIT",transaction_time=datetime.datetime.now(),transaction_amount=amount)
        return transaction
