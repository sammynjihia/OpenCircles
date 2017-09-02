from wallet.models import Transactions
import datetime

class Wallet():
    def  check_balance(self,amount,user):
        actual_balance = user.member.wallet.balance
        if actual_balance >= amount:
            return True
        return False

    def validate_account_info(self,request,amount,pin,recipient_account):
        sender_wallet = request.user.member.wallet
        print type(sender_wallet.balance)
        print type(amount)
        if request.user.check_password(pin):
            if sender_wallet.acc_no != recipient_account:
                if sender_wallet.balance >= amount:
                    return True,""
                message = "Insufficient funds in wallet"
                return False,message
            return False,"Unacceptable transaction.The account number provided is your own"
        return False,"Incorrect pin"

    def validate_account(self,request,pin,amount):
        if request.user.check_password(pin):
            wallet = request.user.member.wallet
            print type(wallet.balance)
            print type(amount)
            if wallet.balance >= amount:
                transaction = self.deduct_wallet_funds(wallet,amount)
                return True,transaction
            return False,"Insufficient funds in wallet"
        return False,"Incorrect pin"

    def deduct_wallet_funds(self,wallet,amount):
        new_balance = wallet.balance - amount
        wallet.balance = new_balance
        wallet.save()
        transaction = Transactions.objects.create(wallet=wallet,transaction_type="DEBIT",transaction_time=datetime.datetime.now(),transaction_amount=amount)
        return transaction
