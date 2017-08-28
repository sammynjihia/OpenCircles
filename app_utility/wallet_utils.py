
class Wallet():
    def  check_balance(self,amount,user):
        actual_balance = user.member.wallet.balance
        if actual_balance >= amount:
            return True
        return False

    def validate_account_info(self,request):
        recipient_account,sender_wallet,pin,amount = request.session['account'],request.user.member.wallet,request.session['pin'],request.session['amount']
        if request.user.check_password(pin):
            if sender_wallet.acc_no != recipient_account:
                if sender_wallet.balance >= amount:
                    return True,""
                message = "Insufficient funds in wallet"
                return False,message
            return False,"Unacceptable transaction.The account number provided is your own."
        return False,"Incorrect pin."

    def validate_account(self,request,pin,amount):
        if request.user.check_password(pin):
            if request.user.member.wallet.balance >= amount:
                return True,""
            return False,"Insufficient funds in wallet"
        return False,"Incorrect pin"
